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
CHECKPOINT = "v1-5-pruned-emaonly.safetensors"
MOVIMIENTO = "v3_sd15_mm.ckpt"
CONTROLNET_PROFUNDIDAD = "control_v11f1p_sd15_depth_fp16.safetensors"
CONTROLNET_LINEAS = "control_v11p_sd15_lineart_fp16.safetensors"

# Cuánto manda cada freno. Subir la profundidad respeta más la sala pero deja
# menos sitio a la gente; bajarla suelta el encuadre. 0,75 es el punto en que la
# sala se reconoce y todavía caben personas delante.
FUERZA_PROFUNDIDAD = 0.75
FUERZA_IDENTIDAD = 0.70

CONTEXTO = 16          # fotogramas que AnimateDiff v3 mira a la vez
SOLAPE = 4


class ComfyCaido(RuntimeError):
    pass


def encendido(url: str = COMFY) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/system_stats", timeout=5):
            return True
    except Exception:
        return False


def vram_libre(url: str = COMFY) -> tuple[int, int]:
    """(libre, total) de la tarjeta en MiB, preguntándoselo al driver.

    NO se usa el `vram_free` de `/system_stats`: ComfyUI informa de lo que tiene
    reservado para sí, no de lo que queda en la tarjeta. Con LM Studio ocupando
    10 GB, ComfyUI seguía diciendo «9.489 MiB libres» y el trabajo habría pasado
    la comprobación para morir de OOM a mitad de la generación. Quien sabe
    cuánta memoria hay de verdad es nvidia-smi.
    """
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            libre, total = r.stdout.strip().splitlines()[0].split(",")
            return int(libre), int(total)
    except Exception:
        pass
    # Sin nvidia-smi, lo de ComfyUI es mejor que nada, pero es optimista.
    with urllib.request.urlopen(f"{url}/system_stats", timeout=10) as r:
        d = json.load(r)
    dev = (d.get("devices") or [{}])[0]
    return (dev.get("vram_free", 0) // 2**20, dev.get("vram_total", 0) // 2**20)


def quien_ocupa_la_gpu() -> str:
    """Un texto corto con quién tiene la tarjeta, para poder decirlo en la web."""
    try:
        r = subprocess.run([str(Path.home() / ".lmstudio" / "bin" / "lms.exe"), "ps"],
                           capture_output=True, text=True, timeout=20)
        # `lms ps` a veces antepone líneas sueltas antes de la cabecera, así que
        # no vale con saltarse la primera: se descarta la cabecera por su nombre.
        nombres = [l.split()[0] for l in (r.stdout or "").splitlines()
                   if l.strip() and not l.startswith("IDENTIFIER")]
        if nombres:
            return f"LM Studio tiene cargado: {', '.join(nombres)}"
    except Exception:
        pass
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
              referencia: Path | None = None,
              ancho: int | None = None, alto: int | None = None,
              fuerza_control: float = FUERZA_PROFUNDIDAD,
              fuerza_identidad: float = FUERZA_IDENTIDAD) -> dict:
    """El grafo entero, listo para POST /prompt."""
    ancho = ancho or B.FORMATO["ancho"]
    alto = alto or B.FORMATO["alto"]
    f = B.FORMATO

    g: dict[str, dict] = {}

    g["1"] = {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": CHECKPOINT}}

    modelo = ["1", 0]
    if referencia is not None and referencia.exists():
        g["2"] = {"class_type": "IPAdapterUnifiedLoader",
                  "inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}}
        g["3"] = {"class_type": "LoadImage",
                  "inputs": {"image": _copiar_a_entradas(referencia)}}
        g["4"] = {"class_type": "IPAdapterAdvanced",
                  "inputs": {"model": ["2", 0], "ipadapter": ["2", 1], "image": ["3", 0],
                             "weight": fuerza_identidad, "weight_type": "linear",
                             "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
                             "embeds_scaling": "V only"}}
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
                          "end_percent": 0.85}}

    g["13"] = {"class_type": "EmptyLatentImage",
               "inputs": {"width": ancho, "height": alto, "batch_size": fotogramas}}
    g["14"] = {"class_type": "KSampler",
               "inputs": {"model": ["6", 0], "seed": semilla, "steps": f["pasos"],
                          "cfg": f["cfg"], "sampler_name": f["muestreador"],
                          "scheduler": f["planificador"], "positive": ["12", 0],
                          "negative": ["12", 1], "latent_image": ["13", 0],
                          "denoise": 1.0}}
    g["15"] = {"class_type": "VAEDecode",
               "inputs": {"samples": ["14", 0], "vae": ["1", 2]}}
    g["16"] = {"class_type": "VHS_VideoCombine",
               "inputs": {"images": ["15", 0], "frame_rate": float(f["fps"]),
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
