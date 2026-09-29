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

ENCUADRE = ("head and shoulders portrait, facing the camera, neutral studio lighting, "
            "plain dark background, sharp focus, photorealistic, 50mm lens")

NEGATIVO = ("text, watermark, logo, cartoon, anime, illustration, painting, 3d render, "
            "deformed face, extra heads, blurry, lowres, multiple people, hands")


def ruta_de(clave: str) -> Path:
    return B.DIR_ELENCO / f"{clave}.png"


def _grafo_retrato(p: B.Personaje) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": C.CHECKPOINT}},
        "2": {"class_type": "CLIPTextEncode",
              "inputs": {"text": f"{p.retrato}, {ENCUADRE}", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": NEGATIVO, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": LADO, "height": LADO, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "seed": p.semilla, "steps": PASOS,
                         "cfg": 7.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
                         "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0], "denoise": 1.0}},
        "6": {"class_type": "VAEDecode",
              "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
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


def referencia_para(personajes: list[str]) -> Path | None:
    """El retrato que guía una escena.

    Si en el plano hay varias personas se usa el retrato de la primera. Meterle
    dos identidades a IP-Adapter a la vez las mezcla y salen dos caras a medio
    camino, que es peor que tener una bien y otra genérica.
    """
    for c in personajes:
        r = ruta_de(c)
        if r.exists():
            return r
    return None
