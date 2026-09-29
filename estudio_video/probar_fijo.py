"""Una escena como IMAGEN FIJA, para poder ajustar sin pagar AnimateDiff.

Un plano animado de tres segundos cuesta entre cuatro y diecisiete minutos, así
que probar un prompt, una luz o una fuerza de ControlNet sale carísimo. La misma
escena en imagen fija cuesta segundos y enseña lo mismo: si en fijo la cantina
sale negra, animada saldrá negra.

Además responde a la pregunta de fondo: cuánta calidad da este modelo cuando NO
se le pone AnimateDiff encima, que es lo que hunde el detalle.

    python probar_fijo.py                          el comedor con una persona
    python probar_fijo.py --camara mesa --quien suri
    python probar_fijo.py --pasos 40 --cfg 6
"""
import argparse
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402


def grafo(control: Path, positivo: str, negativo: str, semilla: int, pasos: int,
          cfg: float, vistas: list[Path], fuerza_control: float,
          arreglar_cara: bool, ancho: int, alto: int) -> dict:
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": C.CHECKPOINT}},
        "1v": {"class_type": "VAELoader", "inputs": {"vae_name": C.VAE}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": positivo, "clip": ["1", 1]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": negativo, "clip": ["1", 1]}},
        "9": {"class_type": "LoadImage", "inputs": {"image": C._copiar_a_entradas(control)}},
        "11": {"class_type": "ControlNetLoader",
               "inputs": {"control_net_name": C.CONTROLNET_PROFUNDIDAD}},
        "12": {"class_type": "ControlNetApplyAdvanced",
               "inputs": {"positive": ["7", 0], "negative": ["8", 0], "control_net": ["11", 0],
                          "image": ["9", 0], "strength": fuerza_control,
                          "start_percent": 0.0, "end_percent": C.HASTA_PROFUNDIDAD}},
        "13": {"class_type": "EmptyLatentImage",
               "inputs": {"width": ancho, "height": alto, "batch_size": 1}},
    }

    modelo = ["1", 0]
    if vistas:
        g["2"] = {"class_type": "IPAdapterUnifiedLoader",
                  "inputs": {"model": ["1", 0], "preset": "PLUS FACE (portraits)"}}
        anterior = None
        for n, v in enumerate(vistas):
            g[f"3_{n}"] = {"class_type": "LoadImage",
                           "inputs": {"image": C._copiar_a_entradas(v)}}
            if anterior is None:
                anterior = [f"3_{n}", 0]
            else:
                g[f"3b_{n}"] = {"class_type": "ImageBatch",
                                "inputs": {"image1": anterior, "image2": [f"3_{n}", 0]}}
                anterior = [f"3b_{n}", 0]
        g["4"] = {"class_type": "IPAdapterAdvanced",
                  "inputs": {"model": ["2", 0], "ipadapter": ["2", 1], "image": anterior,
                             "weight": C.FUERZA_IDENTIDAD, "weight_type": "linear",
                             "combine_embeds": "average" if len(vistas) > 1 else "concat",
                             "start_at": 0.15, "end_at": 0.95,
                             "embeds_scaling": "K+V w/ C penalty"}}
        modelo = ["4", 0]

    g["14"] = {"class_type": "KSampler",
               "inputs": {"model": modelo, "seed": semilla, "steps": pasos, "cfg": cfg,
                          "sampler_name": "dpmpp_2m", "scheduler": "karras",
                          "positive": ["12", 0], "negative": ["12", 1],
                          "latent_image": ["13", 0], "denoise": 1.0}}
    g["15"] = {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["1v", 0]}}

    salida = ["15", 0]
    if arreglar_cara and vistas:
        g["20"] = {"class_type": "UltralyticsDetectorProvider",
                   "inputs": {"model_name": C.DETECTOR_CARAS}}
        g["21"] = {"class_type": "FaceDetailer",
                   "inputs": {"image": salida, "model": modelo, "clip": ["1", 1],
                              "vae": ["1v", 0], "guide_size": 512, "guide_size_for": True,
                              "max_size": 1024, "seed": semilla, "steps": 20, "cfg": cfg,
                              "sampler_name": "dpmpp_2m", "scheduler": "karras",
                              "positive": ["7", 0], "negative": ["8", 0],
                              "denoise": C.DENOISE_CARA, "feather": 8, "noise_mask": True,
                              "force_inpaint": True, "bbox_threshold": 0.45,
                              "bbox_dilation": 10, "bbox_crop_factor": 3.0,
                              "sam_detection_hint": "center-1", "sam_dilation": 0,
                              "sam_threshold": 0.93, "sam_bbox_expansion": 0,
                              "sam_mask_hint_threshold": 0.7,
                              "sam_mask_hint_use_negative": "False", "drop_size": 10,
                              "bbox_detector": ["20", 0], "wildcard": "", "cycle": 1}}
        salida = ["21", 0]

    g["22"] = {"class_type": "SaveImage",
               "inputs": {"images": salida, "filename_prefix": "fijo"}}
    return g


def main() -> int:
    p = argparse.ArgumentParser(description="Una escena en imagen fija, para ajustar barato")
    p.add_argument("--camara", default="comedor", choices=list(B.CAMARAS))
    p.add_argument("--quien", default="suri", help="clave del elenco, o '-' para nadie")
    p.add_argument("--accion", default="sits at a table eating, looking to one side")
    p.add_argument("--pasos", type=int, default=30)
    p.add_argument("--cfg", type=float, default=7.0)
    p.add_argument("--semilla", type=int, default=12345)
    p.add_argument("--control", type=float, default=C.FUERZA_PROFUNDIDAD)
    p.add_argument("--ancho", type=int, default=768)
    p.add_argument("--alto", type=int, default=432)
    p.add_argument("--sin-cara", action="store_true", help="sin FaceDetailer")
    p.add_argument("--extra", default="", help="se añade al principio del prompt")
    args = p.parse_args()

    control = B.DIR_CONTROL / f"{args.camara}_profundidad.png"
    if not control.exists():
        print(f"falta {control}")
        return 1

    vistas: list[Path] = []
    quien = ""
    if args.quien != "-":
        vistas = E.referencia_para([args.quien])
        quien = f"({B.ELENCO[args.quien].breve}:1.3), "

    positivo = f"{args.extra}{quien}{args.accion}, {B.ESTILO}"
    print(f"prompt: {positivo[:150]}...")

    pid = C.encolar(grafo(control, positivo, B.ESTILO_NEGATIVO, args.semilla, args.pasos,
                          args.cfg, vistas, args.control, not args.sin_cara,
                          args.ancho, args.alto))
    salidas = C.esperar(pid)
    imagenes = [s for s in salidas if s.suffix.lower() in (".png", ".jpg")]
    if not imagenes:
        print("no salió imagen")
        return 1

    destino = B.DIR_BIBLIA / "prueba_fija.png"
    shutil.copy2(imagenes[0], destino)
    print(destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
