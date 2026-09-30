"""El casting: se hace UNA vez y ya no se toca.

IP-Adapter no mantiene a un personaje por su nombre, lo mantiene por una imagen.
Así que antes de rodar nada hay que tener el retrato de cada uno, y ese retrato
tiene que ser siempre el mismo fichero: si se regenera, Nadia cambia de cara y
todos los vídeos anteriores dejan de casar con los nuevos.

Por eso `casting()` no pisa lo que ya existe salvo que se le diga. El elenco es
el activo más frágil del estudio: es lo único que no se puede volver a deducir
de la base de datos.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import biblia as B
from . import comfy as C

# Retratos cuadrados y de frente: es lo que mejor lee el codificador de imagen.
LADO = 512
PASOS = 26

# Lo que comparten TODAS las imágenes de referencia de una persona: la misma luz
# y el mismo fondo. Una hoja donde cada vista tiene su propia iluminación le
# enseña a IP-Adapter el decorado en vez de la cara.
ENCUADRE_COMUN = ("face fully visible and unobstructed, neutral studio lighting, "
                  "plain dark background, sharp focus, photorealistic, 50mm lens")

ENCUADRE = ("head and shoulders portrait, whole head inside the frame, "
            "looking straight at the camera, " + ENCUADRE_COMUN)

# Lo de tapar la cara no es una manía: en la primera tanda, a un personaje descrito
# con «gafas de soldar subidas a la frente» el modelo le puso las gafas sobre los
# ojos y una braga hasta la nariz, y a otro lo encuadró de cintura para arriba con
# la coronilla fuera. Un molde con la cara tapada o cortada no le sirve de nada a
# IP-Adapter, que es quien tiene que reconocer a esa persona en cada toma.
NEGATIVO = ("text, watermark, logo, cartoon, anime, illustration, painting, 3d render, "
            "deformed face, extra heads, blurry, lowres, multiple people, hands, "
            "face mask, scarf over face, balaclava, covered face, goggles over eyes, "
            "sunglasses, helmet visor, cropped head, top of head out of frame, "
            "back of head, looking away, full body, wide shot, "
            # De la primera tanda de hojas: vistas partidas en dos y un personaje
            # al que el modelo le pintó los labios de rosa en casi todas.
            "split image, diptych, collage, side by side, two people, duplicate person, "
            "mirrored copy, lipstick, makeup, glossy lips, headless, neck only")


def _negativo_de(p: B.Personaje) -> str:
    """El negativo del casting, con el sexo de esta persona y el sitio donde NO está.

    Las dos añadiduras salen del mismo accidente, que conviene no repetir. A Teo
    se le quitó el mono de trabajo del retrato para que su ropa dejara de ser de
    rayas —las rayas se comían la sala en cada plano—, y se le puso «camiseta
    lisa». Con eso desapareció lo único del texto que decía a la vez «hombre» y
    «esto es un sitio de trabajo», y el casting devolvió una MUJER en ropa
    interior sobre una cama: si le pides a SD 1.5 un retrato de alguien joven con
    una camiseta lisa y no dices nada más, te da el tipo de foto que más veces ha
    visto con esa descripción, que es una sesión de dormitorio.

    Describir bien al personaje no basta, porque en el positivo la palabra
    compite con las otras setenta. Aquí no compite con nada.
    """
    extra = ["underwear, lingerie, bedroom, bed, boudoir, glamour shot, undressed"]
    if p.sexo == "h":
        extra.append("woman, female")
    elif p.sexo == "m":
        extra.append("man, male")
    return NEGATIVO + ", " + ", ".join(extra)


# ── La hoja de personaje ────────────────────────────────────────────────────
# Un retrato frontal le da a IP-Adapter un solo punto de vista, y en cuanto la
# persona gira la cabeza dentro de una escena deja de reconocerla: sale «alguien
# parecido». La hoja de personaje es lo que usa cualquier producción para lo
# mismo —varias vistas de la misma persona, más primeros planos de cara— y aquí
# sirve para dos cosas:
#
#   1. Alimentar a IP-Adapter con TODAS las vistas a la vez (sus embeddings se
#      promedian), con lo que la identidad deja de depender del encuadre.
#   2. Poder mirarla. Si un molde no aguanta de perfil, se ve en la hoja y no
#      cuarenta minutos después, en el vídeo.
#
# Cada vista se genera A PARTIR DEL RETRATO BASE, con el propio IP-Adapter: así
# el de perfil es la misma persona que el frontal y no otra que se le parece.
# Cada vista dice SIEMPRE que hay una sola persona y que la cabeza entra entera.
# Sin eso, la primera tanda salió con vistas partidas en dos (el mismo hombre
# duplicado dentro del cuadro) y con primeros planos que eran un cuello y una
# camisa: «extreme close up of the face only» lo entiende como que la cara puede
# salirse por arriba.
SOLO_UNO = "one person alone, single subject, whole head inside the frame"

# ── El giro: 24 posiciones, una cada 15 grados ──────────────────────────────
# Aviso, porque el resultado no va a ser una vuelta perfecta: SD 1.5 **no tiene
# control de ángulo**. No existe forma de pedirle «gira 15 grados»; solo se le
# puede describir la pose con palabras, y el modelo aproxima. Los ángulos
# frontales y de tres cuartos salen bien, el perfil regular, y los de espaldas
# son los peores porque en las fotos con las que se entrenó casi nadie está de
# espaldas. La vuelta entera sirve como referencia de personaje; no como un
# turnaround de animación, que necesitaría un modelo 3D o un ControlNet de pose.
PASO_GIRO = 15
GRADOS = list(range(0, 360, PASO_GIRO))


def _describir_giro(grados: int) -> str:
    """El ángulo, dicho con las palabras que el modelo sí entiende."""
    g = grados % 360
    lado = "left" if g <= 180 else "right"
    d = g if g <= 180 else 360 - g          # 0..180, simétrico
    if d < 8:
        return "front view, standing and facing the camera directly"
    if d < 38:
        return f"standing and facing the camera, body turned slightly to their {lado}"
    if d < 68:
        return f"three quarter view, standing, body turned to their {lado}"
    if d < 83:
        return f"standing, body turned almost sideways to their {lado}, head in near profile"
    if d < 98:
        return f"full side profile view, standing, facing {lado}"
    if d < 128:
        return f"standing, turned away from the camera, seen from behind at an angle, {lado} side"
    if d < 158:
        return f"seen from behind, three quarter back view, {lado} side"
    return "back view, standing with the back to the camera"


VISTAS = [
    ("frontal", f"looking straight at the camera, head and shoulders, {SOLO_UNO}", 1.00),
    ("tres_cuartos", f"three quarter view, head turned slightly to one side, "
                     f"head and shoulders, {SOLO_UNO}", 0.92),
    ("perfil", f"side view of the head, looking to the left, head and shoulders, {SOLO_UNO}", 0.88),
    ("cara", f"close up portrait, the face fills most of the frame, neutral expression, "
             f"{SOLO_UNO}", 0.95),
    ("cara_hablando", f"close up portrait, mouth slightly open as if talking, "
                      f"looking slightly off camera, {SOLO_UNO}", 0.92),
    ("cara_abajo", f"close up portrait, head tilted down, eyes looking down at something "
                   f"held below, concentrated, {SOLO_UNO}", 0.92),
    ("medio", f"medium shot from the waist up, standing, arms relaxed at the sides, {SOLO_UNO}", 0.85),
]

# Cuánto pesa la referencia al generar cada vista. Muy alto y las siete vistas
# salen iguales (el mismo frontal repetido, que no aporta nada); muy bajo y
# dejan de ser la misma persona. 0,85-1,0 es donde gira la cabeza sin cambiar de
# cara.


def ruta_de(clave: str) -> Path:
    """El retrato base: el ancla de la que cuelga todo lo demás."""
    return B.DIR_ELENCO / f"{clave}.png"


def dir_hoja(clave: str) -> Path:
    return B.DIR_ELENCO / clave


# A las ESCENAS solo van las vistas de cara. El plano medio enseña la ropa
# entera, y con él dentro la referencia se trae el color: una toma de alguien con
# chaqueta verde salió con la cantina entera teñida de verde. La hoja completa
# sigue existiendo para mirarla y para el plano medio hace falta el prompt, no la
# referencia.
VISTAS_DE_CARA = {"frontal", "tres_cuartos", "perfil", "cara", "cara_hablando", "cara_abajo"}


def vistas_de(clave: str, solo_cara: bool = True) -> list[Path]:
    """Las imágenes de referencia de un molde, la base primero.

    Si no hay hoja todavía, devuelve el retrato base solo: el estudio sigue
    funcionando con una referencia, simplemente sujeta peor.
    """
    base = ruta_de(clave)
    fuera = [base] if base.exists() else []
    d = dir_hoja(clave)
    if d.is_dir():
        for nombre, _, _ in VISTAS:
            if nombre == "frontal":
                continue                      # el frontal ya es el retrato base
            if solo_cara and nombre not in VISTAS_DE_CARA:
                continue
            f = d / f"{nombre}.png"
            if f.exists():
                fuera.append(f)
    return fuera


def _grafo_retrato(p: B.Personaje) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": C.CHECKPOINT}},
        "1v": {"class_type": "VAELoader", "inputs": {"vae_name": C.VAE}},
        "2": {"class_type": "CLIPTextEncode",
              "inputs": {"text": f"{p.retrato}, {ENCUADRE}", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": _negativo_de(p), "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": LADO, "height": LADO, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "seed": p.semilla, "steps": PASOS,
                         "cfg": 7.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
                         "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0], "denoise": 1.0}},
        "6": {"class_type": "VAEDecode",
              "inputs": {"samples": ["5", 0], "vae": ["1v", 0]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": f"elenco_{p.clave}"}},
    }


def retratar(clave: str, rehacer: bool = False, aviso=None) -> Path:
    """El retrato de una persona del elenco. Si ya existe, no se toca."""
    p = B.ELENCO[clave]
    destino = ruta_de(clave)
    if destino.exists() and not rehacer:
        return destino
    if not C.encendido():
        raise C.ComfyCaido("ComfyUI no está arrancado (run.bat)")

    B.DIR_ELENCO.mkdir(parents=True, exist_ok=True)
    pid = C.encolar(_grafo_retrato(p))
    salidas = C.esperar(pid, aviso=aviso)
    imagenes = [s for s in salidas if s.suffix.lower() in (".png", ".jpg", ".jpeg")]
    if not imagenes:
        raise C.ComfyCaido(f"el casting de {p.nombre} no dejó imagen")
    shutil.copy2(imagenes[0], destino)
    return destino


def _grafo_vista(p: B.Personaje, vista: str, encuadre: str, peso: float,
                 referencia: Path) -> dict:
    """Una vista de la hoja, generada desde el retrato base con IP-Adapter."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": C.CHECKPOINT}},
        "1v": {"class_type": "VAELoader", "inputs": {"vae_name": C.VAE}},
        "2": {"class_type": "IPAdapterUnifiedLoader",
              "inputs": {"model": ["1", 0], "preset": "PLUS FACE (portraits)"}},
        "3": {"class_type": "LoadImage",
              "inputs": {"image": C._copiar_a_entradas(referencia)}},
        "4": {"class_type": "IPAdapterAdvanced",
              "inputs": {"model": ["2", 0], "ipadapter": ["2", 1], "image": ["3", 0],
                         "weight": peso, "weight_type": "linear",
                         "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
                         "embeds_scaling": "V only"}},
        "5": {"class_type": "CLIPTextEncode",
              "inputs": {"text": f"{p.retrato}, {encuadre}, {ENCUADRE_COMUN}", "clip": ["1", 1]}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": _negativo_de(p), "clip": ["1", 1]}},
        "7": {"class_type": "EmptyLatentImage",
              "inputs": {"width": LADO, "height": LADO, "batch_size": 1}},
        "8": {"class_type": "KSampler",
              "inputs": {"model": ["4", 0], "seed": p.semilla + abs(hash(vista)) % 9973,
                         "steps": PASOS, "cfg": 7.0, "sampler_name": "dpmpp_2m",
                         "scheduler": "karras", "positive": ["5", 0], "negative": ["6", 0],
                         "latent_image": ["7", 0], "denoise": 1.0}},
        "9": {"class_type": "VAEDecode",
              "inputs": {"samples": ["8", 0], "vae": ["1v", 0]}},
        "10": {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0], "filename_prefix": f"hoja_{p.clave}_{vista}"}},
    }


LADO_GIRO = 512
FONDO_GIRO = ("standing in a plain photo studio, seamless light grey background, "
              "even soft studio lighting, full body from head to feet inside the frame, "
              "sharp focus, photorealistic, 50mm lens")


def _grafo_giro(p: B.Personaje, grados: int, pose: str, base: Path,
                cuerpo: Path | None) -> dict:
    """Una posición del giro: cuerpo entero, su ropa, fondo de estudio."""
    positivo = f"({p.breve}:1.2), ({p.vestuario}:1.3), {pose}, {FONDO_GIRO}"
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": C.CHECKPOINT}},
        "1v": {"class_type": "VAELoader", "inputs": {"vae_name": C.VAE}},
        "2": {"class_type": "IPAdapterUnifiedLoader",
              "inputs": {"model": ["1", 0], "preset": "PLUS FACE (portraits)"}},
        "3": {"class_type": "LoadImage", "inputs": {"image": C._copiar_a_entradas(base)}},
        "4": {"class_type": "IPAdapterAdvanced",
              "inputs": {"model": ["2", 0], "ipadapter": ["2", 1], "image": ["3", 0],
                         "weight": 0.45, "weight_type": "linear", "combine_embeds": "concat",
                         "start_at": 0.15, "end_at": 0.95,
                         "embeds_scaling": "K+V w/ C penalty"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": positivo, "clip": ["1", 1]}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": _negativo_de(p) + ", cropped legs, cut off feet", "clip": ["1", 1]}},
        "7": {"class_type": "EmptyLatentImage",
              "inputs": {"width": LADO_GIRO, "height": int(LADO_GIRO * 1.5), "batch_size": 1}},
    }
    modelo = ["4", 0]
    if cuerpo is not None and cuerpo.exists():
        g["4b"] = {"class_type": "LoadImage", "inputs": {"image": C._copiar_a_entradas(cuerpo)}}
        g["4c"] = {"class_type": "IPAdapterAdvanced",
                   "inputs": {"model": modelo, "ipadapter": ["2", 1], "image": ["4b", 0],
                              "weight": 0.45, "weight_type": "linear",
                              "combine_embeds": "concat", "start_at": 0.20, "end_at": 0.85,
                              "embeds_scaling": "K+V w/ C penalty"}}
        modelo = ["4c", 0]

    g["8"] = {"class_type": "KSampler",
              "inputs": {"model": modelo, "seed": p.semilla + grados, "steps": PASOS,
                         "cfg": 7.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
                         "positive": ["5", 0], "negative": ["6", 0],
                         "latent_image": ["7", 0], "denoise": 1.0}}
    g["9"] = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["1v", 0]}}
    g["10"] = {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0], "filename_prefix": f"giro_{p.clave}_{grados:03d}"}}
    return g


def hoja_de_personaje(clave: str, rehacer: bool = False, aviso=None) -> list[Path]:
    """Genera (o devuelve) las vistas de un molde. El frontal es el retrato base."""
    p = B.ELENCO[clave]
    base = retratar(clave, aviso=aviso)          # sin base no hay hoja
    d = dir_hoja(clave)
    d.mkdir(parents=True, exist_ok=True)

    for vista, encuadre, peso in VISTAS:
        if vista == "frontal":
            continue
        destino = d / f"{vista}.png"
        if destino.exists() and not rehacer:
            continue
        pid = C.encolar(_grafo_vista(p, vista, encuadre, peso, base))
        salidas = C.esperar(pid, aviso=aviso)
        imagenes = [s for s in salidas if s.suffix.lower() in (".png", ".jpg", ".jpeg")]
        if not imagenes:
            raise C.ComfyCaido(f"la vista «{vista}» de {p.nombre} no dejó imagen")
        shutil.copy2(imagenes[0], destino)
    return vistas_de(clave)


def dir_giro(clave: str) -> Path:
    return dir_hoja(clave) / "giro"


def giro_de(clave: str) -> list[Path]:
    d = dir_giro(clave)
    return [f for g in GRADOS if (f := d / f"{g:03d}.png").exists()]


def giro_de_personaje(clave: str, rehacer: bool = False, aviso=None) -> list[Path]:
    """La vuelta entera: 24 posiciones de cuerpo completo, con SU ropa.

    Cuerpo completo y fondo liso a propósito: esta serie es la referencia del
    personaje vestido, así que lo que tiene que leerse es la ropa y la silueta,
    no el decorado. La identidad la sostienen el retrato base (cara) y la vista
    de plano medio (ropa), las dos como referencia a la vez.
    """
    p = B.ELENCO[clave]
    base = retratar(clave, aviso=aviso)
    cuerpo = cuerpo_de(clave)
    d = dir_giro(clave)
    d.mkdir(parents=True, exist_ok=True)

    hechas = []
    for grados in GRADOS:
        destino = d / f"{grados:03d}.png"
        if destino.exists() and not rehacer:
            hechas.append(destino)
            continue
        pose = _describir_giro(grados)
        pid = C.encolar(_grafo_giro(p, grados, pose, base, cuerpo))
        salidas = C.esperar(pid, aviso=aviso)
        imagenes = [s for s in salidas if s.suffix.lower() in (".png", ".jpg", ".jpeg")]
        if not imagenes:
            raise C.ComfyCaido(f"el giro {grados}° de {p.nombre} no dejó imagen")
        shutil.copy2(imagenes[0], destino)
        hechas.append(destino)
    return hechas


def giros(rehacer: bool = False, solo: list[str] | None = None, aviso=None) -> dict[str, str]:
    out: dict[str, str] = {}
    for clave in (solo or list(B.ELENCO)):
        try:
            out[clave] = f"{len(giro_de_personaje(clave, rehacer=rehacer, aviso=aviso))} posiciones"
        except Exception as e:
            out[clave] = f"ERROR: {e}"
    return out


def hojas(rehacer: bool = False, solo: list[str] | None = None, aviso=None) -> dict[str, str]:
    """La hoja de todo el elenco."""
    out: dict[str, str] = {}
    for clave in (solo or list(B.ELENCO)):
        try:
            v = hoja_de_personaje(clave, rehacer=rehacer, aviso=aviso)
            out[clave] = f"{len(v)} vistas"
        except Exception as e:
            out[clave] = f"ERROR: {e}"
    return out


def falta_hoja() -> list[str]:
    return [c for c in B.ELENCO if len(vistas_de(c)) < len(VISTAS)]


def casting(rehacer: bool = False, solo: list[str] | None = None, aviso=None) -> dict[str, str]:
    """Retrata a todo el elenco. Devuelve clave → ruta o motivo del fallo."""
    out: dict[str, str] = {}
    for clave in (solo or list(B.ELENCO)):
        try:
            out[clave] = str(retratar(clave, rehacer=rehacer, aviso=aviso))
        except Exception as e:
            out[clave] = f"ERROR: {e}"
    return out


def falta_casting() -> list[str]:
    return [c for c in B.ELENCO if not ruta_de(c).exists()]


def cuerpo_de(clave: str) -> Path | None:
    """La vista de plano medio: la que enseña la ropa entera.

    Va por separado de las de cara porque cumple otro papel y necesita otro
    peso: la cara manda en quién es, y esta en qué lleva puesto. Metida en el
    mismo montón, teñía la escena con el color de la ropa.
    """
    f = dir_hoja(clave) / "medio.png"
    return f if f.exists() else None


def referencia_para(personajes: list[str]) -> list[Path]:
    """Las imágenes de referencia que guían una escena.

    Se usa la hoja ENTERA de la primera persona del plano: frontal, tres cuartos,
    perfil y los primeros planos de cara. IP-Adapter promedia sus embeddings, así
    que la identidad deja de depender de cómo esté colocada la cabeza en la toma.

    De una sola persona, eso sí. Meterle DOS identidades a la vez las mezcla y
    salen dos caras a medio camino, que es peor que tener una bien y otra
    genérica.
    """
    for c in personajes:
        v = vistas_de(c)
        if v:
            return v
    return []
