"""¿Lleva la misma ropa en las cuatro tomas?

La cara se sujeta con IP-Adapter, pero la ropa se le escapaba: el mismo hombre
salía con chaleco reflectante en un plano y con chaleco y pajarita en el
siguiente. Y la ropa es parte del personaje tanto como la cara.

Esta prueba pone a cada molde en las cuatro cámaras, una fila por persona, para
poder mirar la fila entera y decir si es la misma ropa o no. En imágenes fijas,
que cuestan 40 segundos y no cuatro minutos.

    python probar_vestuario.py --solo klaus
    python probar_vestuario.py
"""
import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402

TOMAS = [
    ("entrada", "walks in through the doorway and looks around"),
    ("comedor", "walks between the tables"),
    ("mesa", "sits at the table holding a phone, looking down at it"),
    ("atraque", "stands at the counter waiting"),
]
LADO = 340


def main() -> int:
    p = argparse.ArgumentParser(description="¿Aguanta la ropa entre tomas?")
    p.add_argument("--solo", default="")
    p.add_argument("--pasos", type=int, default=28)
    args = p.parse_args()

    claves = [c.strip() for c in args.solo.split(",") if c.strip()] or list(B.ELENCO)
    destino = B.DIR_BIBLIA / "vestuario"
    destino.mkdir(parents=True, exist_ok=True)

    hechas: dict[str, list[Path]] = {}
    for clave in claves:
        p_ = B.ELENCO[clave]
        vistas = E.referencia_para([clave])
        cuerpo = E.cuerpo_de(clave)
        fila = []
        for n, (camara, accion) in enumerate(TOMAS):
            control = B.DIR_CONTROL / f"{camara}_profundidad.png"
            positivo = (f"({p_.breve}:1.3), ({p_.vestuario}:1.2), {accion}, {B.ESTILO}")
            grafo = C.construir_fijo(
                prompt_positivo=positivo, prompt_negativo=B.ESTILO_NEGATIVO,
                control=control, semilla=p_.semilla + n * 17,
                prefijo=f"vest_{clave}_{n}", referencia=vistas, cuerpo=cuerpo,
                pasos=args.pasos)
            salidas = C.esperar(C.encolar(grafo))
            imgs = [s for s in salidas if s.suffix.lower() in (".png", ".jpg")]
            if not imgs:
                print(f"  {clave} toma {n+1}: sin imagen")
                continue
            f = destino / f"{clave}_{n}.png"
            shutil.copy2(imgs[0], f)
            fila.append(f)
            print(f"  {clave} · toma {n+1}/{len(TOMAS)} ({camara})")
        hechas[clave] = fila

    filas = [(k, v) for k, v in hechas.items() if v]
    if not filas:
        return 1
    ancho = LADO * len(TOMAS) + 12 * (len(TOMAS) + 1)
    alto_fila = LADO * 9 // 16 + 34
    hoja = Image.new("RGB", (ancho, alto_fila * len(filas) + 20), (16, 13, 12))
    dib = ImageDraw.Draw(hoja)
    for f, (clave, imgs) in enumerate(filas):
        y = 12 + f * alto_fila
        dib.text((12, y - 2), B.ELENCO[clave].nombre, fill=(233, 228, 222))
        for c, img in enumerate(imgs):
            im = Image.open(img).convert("RGB")
            im = im.resize((LADO, LADO * im.height // im.width))
            hoja.paste(im, (12 + c * (LADO + 12), y + 14))

    salida = B.DIR_BIBLIA / "prueba_vestuario.png"
    hoja.save(salida)
    print(f"\n{salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
