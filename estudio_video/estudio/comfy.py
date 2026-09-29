"""El motor: AnimateDiff sobre SD 1.5, atado corto por ControlNet e IP-Adapter.

El grafo se monta aquí a mano, en vez de cargar un .json exportado de la
interfaz, por un motivo práctico: un workflow exportado guarda también la
posición de las cajitas en pantalla y se rompe en cuanto alguien mueve una. Lo
que importa son las conexiones, y aquí están a la vista.

Tres frenos a la invención del modelo, de mayor a menor:

  1. **ControlNet depth** con el mapa de la cámara (`geometria.py`). Es el que
     dice dónde está cada muro. Sin esto no hay estudio: hay lotería.
  2. **IP-Adapter** con el retrato del personaje. Es el que hace que Nadia sea
     Nadia en la toma tres y en la veinte.
  3. **Semilla derivada del guion**. El mismo guion da el mismo vídeo. Si algo
     sale mal, se puede repetir exactamente y comparar.

Sobre el hardware: la 1080 Ti es Pascal. Sin BF16 ni FP8, y por eso el modelo es
SD 1.5 y no algo de este año. A cambio entra entero en 11 GB y va a una
velocidad utilizable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from . import biblia as B

COMFY = "http://127.0.0.1:8188"

# El modelo importa MÁS que la resolución. `v1-5-pruned-emaonly` es SD 1.5 pelado
# de 2022 y no sabe hacer una foto: da caras de cera y anatomía rara. Realistic
# Vision es la misma arquitectura —así que AnimateDiff, ControlNet e IP-Adapter
# siguen valiendo— afinada para fotorrealismo. Cambiar esto fue lo que más
# acercó el resultado a una fotografía, más que subir píxeles o pasos.
CHECKPOINT = "realisticVision_v60B1.safetensors"
# El VAE del checkpoint es el flojo de serie: el ft-mse recupera color y detalle
# fino, sobre todo en piel y en las zonas oscuras, que aquí son casi todas.
VAE = "vae-ft-mse-840000-ema-pruned.safetensors"
MOVIMIENTO = "v3_sd15_mm.ckpt"

# Reparación de caras: detecta cada cara, la regenera a 512 px y la vuelve a
# pegar. En un plano general la cara ocupa veinte píxeles y el modelo no puede
# resolverla; esto le da esos mismos veinte píxeles ampliados y vuelve a
# dibujarlos con todo el modelo. Es lo que separa «figura con manchas en la
# cabeza» de «persona».
DETECTOR_CARAS = "bbox/face_yolov8m.pt"
DENOISE_CARA = 0.45        # más alto reinventa la cara; más bajo no la arregla
CONTROLNET_PROFUNDIDAD = "control_v11f1p_sd15_depth_fp16.safetensors"
CONTROLNET_LINEAS = "control_v11p_sd15_lineart_fp16.safetensors"

# Cuánto manda cada freno. Subir la profundidad respeta más la sala pero deja
# menos sitio a la gente; bajarla suelta el encuadre.
#
# Medido con el primer clip (29/09/2026): con 0,75 hasta el 85% de los pasos, la
# sala salía perfecta —muro, puerta, suelo, el bulto de las sillas— y NO HABÍA
# NADIE. El mapa de profundidad no tiene personas dentro, así que mientras
# ControlNet manda, el modelo rellena lo que ve: una habitación vacía. Aflojarlo
# y, sobre todo, soltarlo a mitad de camino deja que la gente aparezca cuando la
# sala ya está puesta.
FUERZA_PROFUNDIDAD = 0.65
HASTA_PROFUNDIDAD = 0.70       # a partir de ahí, ControlNet ya no opina
# La identidad, floja: con la cara basta. Subirla trae también la ropa, la luz y
# el fondo del retrato, y la escena deja de ser la cantina. Medido: con 0,75 y
# una referencia de alguien con chaqueta verde, la cantina entera salió verde
# —paredes, techo y suelo—, y a 0,60 seguía igual. El color viaja en el
# embedding aunque el adaptador sea el de caras, porque en un primer plano
# también hay cuello y ropa.
FUERZA_IDENTIDAD = 0.45

CONTEXTO = 16          # fotogramas que AnimateDiff v3 mira a la vez
SOLAPE = 4

# Superresolución: sube lo generado hasta 1080 inventando detalle. Sin esto, el
# montaje solo estira píxeles y el resultado es un 768 grande y blando.
#
# x2 y no x4: de 768x432 a 1080 hay un factor 2,5, así que un x4 sube primero a
# 3072x1728 para tener que bajar después. Medido: con el x4, un plano de tres
# segundos costaba 7,1 minutos; casi la mitad era escalar de más.
ESCALADOR = "RealESRGAN_x2plus.pth"
ALTO_FINAL = 1080


class ComfyCaido(RuntimeError):
    pass


def encendido(url: str = COMFY) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/system_stats", timeout=5):
            return True
    except Exception:
        return False


def _nvidia_smi() -> tuple[int, int] | None:
    """(libre, total) en MiB según el driver, o None si no se puede preguntar."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            libre, total = (int(x) for x in r.stdout.strip().splitlines()[0].split(","))
            return libre, total
    except Exception:
        pass
    return None


def _comfy_stats(url: str) -> dict:
    with urllib.request.urlopen(f"{url}/system_stats", timeout=10) as r:
        return (json.load(r).get("devices") or [{}])[0]


def modelos_de_lm_studio() -> list[str]:
    """Qué tiene cargado LM Studio, que es el único que compite de verdad aquí."""
    try:
        r = subprocess.run([str(Path.home() / ".lmstudio" / "bin" / "lms.exe"), "ps"],
                           capture_output=True, text=True, timeout=25)
        return [l.split()[0] for l in (r.stdout or "").splitlines()
                if l.strip() and not l.startswith("IDENTIFIER")
                and not l.startswith("No models")]
    except Exception:
        return []


def vram_libre(url: str = COMFY) -> tuple[int, int]:
    """Cuánta VRAM hay DISPONIBLE PARA GENERAR, en MiB, y el total.

    Ninguna de las dos fuentes vale por sí sola, y las dos se equivocaron en un
    sentido distinto el mismo día:

    · **ComfyUI** (`/system_stats`) no ve la memoria de otros procesos. Con LM
      Studio ocupando 10 de 11 GB seguía diciendo «9.489 MiB libres», y el
      trabajo habría pasado la comprobación para morir de OOM a mitad.
    · **nvidia-smi** no distingue quién ocupa qué. Cuando ComfyUI tiene sus
      propios modelos cargados —7,5 GB tras generar las hojas— el driver dice
      que la tarjeta está llena, y el estudio se negaba a generar por culpa de
      sí mismo, cuando ComfyUI descarga lo que le sobra en cuanto lo necesita.

    La regla, que es la de esta máquina: si LM Studio tiene algo cargado, manda
    el driver, porque esa memoria no la va a soltar nadie. Si no, manda ComfyUI,
    que sabe gestionar la suya.
    """
    driver = _nvidia_smi()
    try:
        dev = _comfy_stats(url)
        comfy_libre = dev.get("vram_free", 0) // 2**20
        comfy_total = dev.get("vram_total", 0) // 2**20
    except Exception:
        return driver or (0, 0)

    if not driver:
        return comfy_libre, comfy_total
    libre_driver, total = driver
    if modelos_de_lm_studio():
        return libre_driver, total
    return max(libre_driver, comfy_libre), total


def quien_ocupa_la_gpu() -> str:
    """Un texto corto con quién tiene la tarjeta, para poder decirlo en la web."""
    nombres = modelos_de_lm_studio()
    if nombres:
        return (f"LM Studio tiene cargado: {', '.join(nombres)}. "
                f"Se libera con `lms unload {nombres[0]}`")
    return "hay otro proceso usando la tarjeta"


def _copiar_a_entradas(origen: Path) -> str:
    """LoadImage solo mira su carpeta de entrada; se copia allí y se usa el nombre."""
    entradas = B.DIR_COMFY_ENTRADAS
    entradas.mkdir(parents=True, exist_ok=True)
    destino = entradas / origen.name
    if not destino.exists() or destino.stat().st_mtime < origen.stat().st_mtime:
        shutil.copy2(origen, destino)
    return destino.name


def construir(prompt_positivo: str, prompt_negativo: str, control: Path,
              fotogramas: int, semilla: int, prefijo: str,
              referencia: Path | list[Path] | None = None,
              ancho: int | None = None, alto: int | None = None,
              fuerza_control: float = FUERZA_PROFUNDIDAD,
              fuerza_identidad: float = FUERZA_IDENTIDAD,
              escalar: bool = True, arreglar_caras: bool = True) -> dict:
    """El grafo entero, listo para POST /prompt."""
    ancho = ancho or B.FORMATO["ancho"]
    alto = alto or B.FORMATO["alto"]
    f = B.FORMATO

    g: dict[str, dict] = {}

    g["1"] = {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": CHECKPOINT}}
    g["1v"] = {"class_type": "VAELoader", "inputs": {"vae_name": VAE}}
    vae = ["1v", 0]

    # La referencia puede ser una imagen o la hoja de personaje entera. Con la
    # hoja, las vistas se apilan en un lote y sus embeddings se PROMEDIAN: así la
    # identidad no depende de que en la toma la cabeza esté como en el retrato.
    vistas = ([referencia] if isinstance(referencia, Path) else list(referencia or []))
    vistas = [v for v in vistas if v and v.exists()]

    modelo = ["1", 0]
    if vistas:
        # PLUS FACE y no PLUS: el primero mira la CARA, el segundo mira la imagen
        # entera y se trae el color y el estilo con ella. Con PLUS, una toma de
        # alguien con chaqueta verde salió con la cantina entera teñida de verde,
        # paredes incluidas. Aquí de la referencia solo queremos la persona.
        g["2"] = {"class_type": "IPAdapterUnifiedLoader",
                  "inputs": {"model": ["1", 0], "preset": "PLUS FACE (portraits)"}}
        # Una carga por vista, encadenadas con ImageBatch hasta formar un lote.
        anterior = None
        for n, v in enumerate(vistas):
            carga = f"3_{n}"
            g[carga] = {"class_type": "LoadImage",
                        "inputs": {"image": _copiar_a_entradas(v)}}
            if anterior is None:
                anterior = [carga, 0]
            else:
                junta = f"3b_{n}"
                g[junta] = {"class_type": "ImageBatch",
                            "inputs": {"image1": anterior, "image2": [carga, 0]}}
                anterior = [junta, 0]

        g["4"] = {"class_type": "IPAdapterAdvanced",
                  "inputs": {"model": ["2", 0], "ipadapter": ["2", 1], "image": anterior,
                             "weight": fuerza_identidad, "weight_type": "linear",
                             "combine_embeds": "average" if len(vistas) > 1 else "concat",
                             # Entra una vez puesta la escena: en los primeros
                             # pasos se decide la composición y el color, y ahí
                             # la referencia no pinta nada bueno.
                             "start_at": 0.15, "end_at": 0.95,
                             # «C penalty» castiga la transferencia de estilo y
                             # deja pasar sobre todo el parecido de la cara.
                             "embeds_scaling": "K+V w/ C penalty"}}
        modelo = ["4", 0]

    # Contexto estático: no hace falta el deslizante para clips de pocos
    # segundos, y además evita depender de la lista de `context_schedule`, que
    # ComfyUI no publica y cambia de nombres entre versiones del nodo.
    g["5"] = {"class_type": "ADE_StandardStaticContextOptions",
              "inputs": {"context_length": CONTEXTO, "context_overlap": SOLAPE}}
    g["6"] = {"class_type": "ADE_AnimateDiffLoaderWithContext",
              "inputs": {"model": modelo, "model_name": MOVIMIENTO,
                         "beta_schedule": "autoselect", "context_options": ["5", 0]}}

    g["7"] = {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt_positivo, "clip": ["1", 1]}}
    g["8"] = {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt_negativo, "clip": ["1", 1]}}

    # El mapa de control es UNA imagen que vale para todos los fotogramas: la
    # cámara no se mueve dentro de un plano. Eso es lo que clava la sala.
    g["9"] = {"class_type": "LoadImage",
              "inputs": {"image": _copiar_a_entradas(control)}}
    g["10"] = {"class_type": "RepeatImageBatch",
               "inputs": {"image": ["9", 0], "amount": fotogramas}}
    g["11"] = {"class_type": "ControlNetLoader",
               "inputs": {"control_net_name": CONTROLNET_PROFUNDIDAD}}
    g["12"] = {"class_type": "ControlNetApplyAdvanced",
               "inputs": {"positive": ["7", 0], "negative": ["8", 0],
                          "control_net": ["11", 0], "image": ["10", 0],
                          "strength": fuerza_control, "start_percent": 0.0,
                          "end_percent": HASTA_PROFUNDIDAD}}

    g["13"] = {"class_type": "EmptyLatentImage",
               "inputs": {"width": ancho, "height": alto, "batch_size": fotogramas}}
    g["14"] = {"class_type": "KSampler",
               "inputs": {"model": ["6", 0], "seed": semilla, "steps": f["pasos"],
                          "cfg": f["cfg"], "sampler_name": f["muestreador"],
                          "scheduler": f["planificador"], "positive": ["12", 0],
                          "negative": ["12", 1], "latent_image": ["13", 0],
                          "denoise": 1.0}}
    g["15"] = {"class_type": "VAEDecode",
               "inputs": {"samples": ["14", 0], "vae": vae}}

    imagenes = ["15", 0]

    # Reparar las caras ANTES de escalar: así el detalle que inventa el escalador
    # parte de una cara bien dibujada y no de un borrón nítido.
    if arreglar_caras:
        g["20"] = {"class_type": "UltralyticsDetectorProvider",
                   "inputs": {"model_name": DETECTOR_CARAS}}
        g["21"] = {"class_type": "FaceDetailer",
                   "inputs": {
                       "image": imagenes, "model": modelo, "clip": ["1", 1], "vae": vae,
                       "guide_size": 512, "guide_size_for": True, "max_size": 1024,
                       "seed": semilla, "steps": 18, "cfg": f["cfg"],
                       "sampler_name": "dpmpp_2m", "scheduler": "karras",
                       "positive": ["7", 0], "negative": ["8", 0],
                       "denoise": DENOISE_CARA, "feather": 8, "noise_mask": True,
                       "force_inpaint": True, "bbox_threshold": 0.45,
                       "bbox_dilation": 10, "bbox_crop_factor": 3.0,
                       "sam_detection_hint": "center-1", "sam_dilation": 0,
                       "sam_threshold": 0.93, "sam_bbox_expansion": 0,
                       "sam_mask_hint_threshold": 0.7,
                       "sam_mask_hint_use_negative": "False",
                       "drop_size": 10, "bbox_detector": ["20", 0],
                       "wildcard": "", "cycle": 1}}
        imagenes = ["21", 0]

    # Superresolución antes de guardar: con modelo y luego encaje exacto a
    # 1920x1080. Se hace aquí y no en ffmpeg porque el modelo reconstruye
    # detalle (bordes, tela, cara) y un escalado de vídeo solo interpola.
    if escalar:
        g["17"] = {"class_type": "UpscaleModelLoader",
                   "inputs": {"model_name": ESCALADOR}}
        g["18"] = {"class_type": "ImageUpscaleWithModel",
                   "inputs": {"upscale_model": ["17", 0], "image": imagenes}}
        g["19"] = {"class_type": "ImageScale",
                   "inputs": {"image": ["18", 0], "upscale_method": "lanczos",
                              "width": int(ALTO_FINAL * ancho / alto), "height": ALTO_FINAL,
                              "crop": "disabled"}}
        imagenes = ["19", 0]

    g["16"] = {"class_type": "VHS_VideoCombine",
               "inputs": {"images": imagenes, "frame_rate": float(f["fps"]),
                          "loop_count": 0, "filename_prefix": prefijo,
                          "format": "video/h264-mp4", "pingpong": False,
                          "save_output": True}}
    return g


def encolar(grafo: dict, url: str = COMFY) -> str:
    cliente = str(uuid.uuid4())
    cuerpo = json.dumps({"prompt": grafo, "client_id": cliente}).encode()
    pet = urllib.request.Request(f"{url}/prompt", data=cuerpo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pet, timeout=60) as r:
            return json.load(r)["prompt_id"]
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")[:1500]
        raise ComfyCaido(f"ComfyUI rechazó el grafo: {detalle}") from e
    except urllib.error.URLError as e:
        raise ComfyCaido(f"ComfyUI no responde en {url}: {e}") from e


def esperar(prompt_id: str, url: str = COMFY, limite: int = 3600,
            aviso=None) -> list[Path]:
    """Espera a que termine y devuelve los ficheros que dejó.

    `aviso(segundos, estado)` se llama cada pocos segundos para poder pintar
    progreso en la web sin tener que abrir un websocket.
    """
    inicio = time.time()
    while True:
        if time.time() - inicio > limite:
            raise ComfyCaido(f"la generación pasó de {limite} s")
        try:
            with urllib.request.urlopen(f"{url}/history/{prompt_id}", timeout=30) as r:
                hist = json.load(r)
        except Exception:
            hist = {}

        if prompt_id in hist:
            datos = hist[prompt_id]
            estado = datos.get("status", {})
            if estado.get("status_str") == "error" or not estado.get("completed", True):
                mensajes = estado.get("messages", [])
                raise ComfyCaido(f"la generación falló: {json.dumps(mensajes)[:1200]}")
            salidas: list[Path] = []
            for nodo in datos.get("outputs", {}).values():
                for clave in ("gifs", "videos", "images"):
                    for f in nodo.get(clave, []) or []:
                        carpeta = (B.DIR_COMFY_SALIDAS if f.get("type") == "output"
                                   else B.DIR_COMFY_TEMP)
                        sub = f.get("subfolder") or ""
                        salidas.append(carpeta / sub / f["filename"])
            return [s for s in salidas if s.suffix.lower() in (".mp4", ".webm", ".gif")] or salidas

        if aviso:
            try:
                with urllib.request.urlopen(f"{url}/queue", timeout=10) as r:
                    cola = json.load(r)
                pendientes = len(cola.get("queue_pending", [])) + len(cola.get("queue_running", []))
            except Exception:
                pendientes = -1
            aviso(int(time.time() - inicio), f"en cola ({pendientes} por delante)")
        time.sleep(3)


def interrumpir(url: str = COMFY) -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(f"{url}/interrupt", data=b""), timeout=10)
    except Exception:
        pass
