"""Anima un plano YA GENERADO con WAN 2.2 TI2V-5B (imagen→vídeo).

    python probar_wan.py <imagen.png> "lo que hace la persona" [--fotogramas 17]

La idea, y por qué este camino y no texto→vídeo: la consistencia de personaje
—cara, ropa, que sea SIEMPRE el mismo— ya está resuelta en el lado de la imagen
fija, con IP-Adapter, las hojas de personaje y ControlNet. Pedirle a un modelo de
vídeo que la resuelva otra vez desde el texto es rehacer lo que ya funciona y
además perderlo. Partiendo del plano aprobado como primer fotograma, la
identidad y la nitidez vienen dadas y el modelo solo pone el movimiento.

Es lo contrario de lo que hacía AnimateDiff, que reinventaba la escena en cada
fotograma: por eso la sala derivaba a otra habitación, la gente se disolvía y
todo salía blando.

El modelo va en GGUF porque en 11 GB no entra de otra forma, y el codificador de
texto (umT5-XXL) es más grande que el propio modelo de vídeo, así que ComfyUI
tiene que descargarlo de la VRAM después de usarlo.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import comfy as C           # noqa: E402

MODELO = "Wan2.2-TI2V-5B-Q5_K_M.gguf"
CODIFICADOR = "umt5-xxl-encoder-Q5_K_M.gguf"
VAE = "Wan2.2_VAE.safetensors"

# El TI2V-5B se entrenó a 1280x704, y conviene darle ese tamaño: a 704x384 la
# cara de una persona sentada ocupa unos 60 píxeles y el modelo no tiene dónde
# poner los rasgos, así que los reinventa. El tamaño NO es un lujo aquí, es lo
# que decide si la cara se reconoce.
ANCHO, ALTO = 1280, 704
DESPLAZAMIENTO = 8.0          # `shift` de ModelSamplingSD3; lo que pide WAN 2.2

NEGATIVO = ("blurry, lowres, jpeg artifacts, distorted hands, extra fingers, "
            "deformed face, cartoon, anime, illustration, 3d render, watermark, "
            "text, static, still image, frozen")


def grafo(imagen: Path, accion: str, fotogramas: int, prefijo: str,
          ancho: int = ANCHO, alto: int = ALTO, pasos: int = 20) -> dict:
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": MODELO}},
        "2": {"class_type": "CLIPLoaderGGUF",
              "inputs": {"clip_name": CODIFICADOR, "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        # WAN 2.2 no usa el muestreo por defecto: sin este nodo el movimiento
        # sale a tirones y el color se va.
        "4": {"class_type": "ModelSamplingSD3",
              "inputs": {"model": ["1", 0], "shift": DESPLAZAMIENTO}},
        "5": {"class_type": "LoadImage",
              "inputs": {"image": C._copiar_a_entradas(imagen)}},
        # El plano fijo viene a 3072x1728 (se escaló x4 para que la cámara
        # pudiera acercarse). Aquí sobra: se baja al tamaño del modelo.
        "6": {"class_type": "ImageScale",
              "inputs": {"image": ["5", 0], "upscale_method": "lanczos",
                         "width": ancho, "height": alto, "crop": "center"}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": accion, "clip": ["2", 0]}},
        "8": {"class_type": "CLIPTextEncode",
              "inputs": {"text": NEGATIVO, "clip": ["2", 0]}},
        "9": {"class_type": "Wan22ImageToVideoLatent",
              "inputs": {"vae": ["3", 0], "width": ancho, "height": alto,
                         "length": fotogramas, "batch_size": 1,
                         "start_image": ["6", 0]}},
        "10": {"class_type": "KSampler",
               "inputs": {"model": ["4", 0], "seed": 90210, "steps": pasos, "cfg": 5.0,
                          "sampler_name": "uni_pc", "scheduler": "simple",
                          "positive": ["7", 0], "negative": ["8", 0],
                          "latent_image": ["9", 0], "denoise": 1.0}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "VHS_VideoCombine",
               "inputs": {"images": ["11", 0], "frame_rate": 16.0, "loop_count": 0,
                          "filename_prefix": prefijo, "format": "video/h264-mp4",
                          "pingpong": False, "save_output": True}},
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Prueba de WAN 2.2 imagen→vídeo")
    p.add_argument("imagen")
    p.add_argument("accion")
    # 4n+1: el VAE de WAN comprime el tiempo de cuatro en cuatro y el primer
    # fotograma es el de la imagen, así que las longitudes válidas son 17, 33...
    p.add_argument("--fotogramas", type=int, default=17)
    p.add_argument("--ancho", type=int, default=ANCHO)
    p.add_argument("--alto", type=int, default=ALTO)
    p.add_argument("--pasos", type=int, default=20)
    args = p.parse_args()

    img = Path(args.imagen).resolve()
    if not img.exists():
        print(f"no existe: {img}")
        return 1

    g = grafo(img, args.accion, args.fotogramas, f"wan_{args.ancho}_{img.stem[:20]}",
          ancho=args.ancho, alto=args.alto, pasos=args.pasos)
    t0 = time.time()
    try:
        salidas = C.esperar(C.encolar(g), aviso=lambda s, e: print(f"  {e}, {s} s"))
    except Exception as e:
        print(f"FALLÓ: {e}")
        return 1
    dur = time.time() - t0
    seg = args.fotogramas / 16
    print(f"\n{args.fotogramas} fotogramas ({seg:.1f} s de vídeo) en {dur/60:.1f} min "
          f"→ {dur/seg:.0f} s de GPU por segundo de vídeo")
    for s in salidas:
        print(" ", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
