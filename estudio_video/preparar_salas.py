"""Genera la CANTINA VACÍA, una imagen por cámara, y la guarda como dato fijo.

    python preparar_salas.py mesa comedor        unas cámaras
    python preparar_salas.py                     todas las que tengan mapa

Esto existe porque la sala se reinventaba en cada plano. Mismo mapa de
profundidad, mismo mapa de líneas, misma descripción en el prompt y hasta la
misma semilla, y aun así dos planos de la MISMA cámara salían en habitaciones
distintas: una oscura con cortinas, otra clara con puertas de madera. Un vídeo
de tres planos parecía rodado en tres sitios.

Lo que decide el color de las paredes, el material de las sillas y la luz no es
ninguna de esas cosas: es el ruido del que parte cada generación. Y no hay
número que lo arregle —subir ControlNet unifica la sala pero echa a la persona
del cuadro, medido tres veces el 01/10/2026—.

Así que la sala pasa a ser un DATO, como ya lo eran la cara y la ropa: se genera
una vez, se mira, se aprueba y se guarda en `biblia/salas/`. Después cada plano
PARTE de ella en vez de partir de ruido, y el modelo solo tiene que meter a la
persona dentro.

Las imágenes se miran antes de darlas por buenas. Si una cámara sale fea, se
vuelve a tirar con otra semilla (`--semilla`) hasta que guste: es una decisión
que se toma UNA vez y luego la hereda cada vídeo.
"""
import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402

DIR_SALAS = AQUI / "biblia" / "salas"

# Qué se le pide a cada cámara ADEMÁS del estilo común. Hace falta porque
# `B.ESTILO` dice «comedor de tripulación de una estación espacial», y eso en la
# cocina da una habitación de acero vacía, sin plancha ni freidora: el estilo
# describe el local, no cada zona. La zona la pone esto.
#
# Lo que NO se pide en ninguna: gente. Las salas son el decorado; las personas
# las mete después cada plano.
ZONAS = {
    "cocina": "a professional kitchen, hot plate, deep fryer, extractor hood, "
              "steel worktops, pots and pans, shelves with containers",
    "pase": "a kitchen pass, heated pass shelf, plates waiting under warm lamps, "
            "order rail, steel counter between kitchen and dining room",
    "atraque": "a bar counter, bottles on backlit shelves, taps, glasses, "
               "stools along the bar",
    "recogida": "a pickup point, shelves with bags and boxes ready to collect",
}


def prompt_de_sala(camara: str) -> str:
    """El estilo común del local, más lo que distingue a esa zona."""
    zona = ZONAS.get(camara)
    return f"{zona}, {B.ESTILO}" if zona else B.ESTILO


def camaras_con_mapa() -> list[str]:
    return sorted(p.stem.replace("_profundidad", "")
                  for p in B.DIR_CONTROL.glob("*_profundidad.png"))


def main() -> int:
    p = argparse.ArgumentParser(description="Genera la cantina vacía por cámara")
    p.add_argument("camaras", nargs="*", help="vacío = todas las que tengan mapa")
    p.add_argument("--semilla", type=int, default=B.FORMATO["semilla_base"])
    args = p.parse_args()

    DIR_SALAS.mkdir(parents=True, exist_ok=True)
    camaras = args.camaras or camaras_con_mapa()
    for cam in camaras:
        prof = B.DIR_CONTROL / f"{cam}_profundidad.png"
        if not prof.exists():
            print(f"{cam}: sin mapa de profundidad, se salta")
            continue
        lineas = B.DIR_CONTROL / f"{cam}_lineas.png"
        g = C.construir_sala(
            control=prof, lineas=lineas if lineas.exists() else None,
            prompt_sala=prompt_de_sala(cam), semilla=args.semilla, prefijo=f"sala_{cam}")
        salidas = C.esperar(C.encolar(g))
        imgs = [s for s in salidas if s.suffix.lower() == ".png"]
        if not imgs:
            print(f"{cam}: no salió imagen")
            continue
        destino = DIR_SALAS / f"{cam}.png"
        destino.write_bytes(imgs[0].read_bytes())
        print(f"{cam}: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
