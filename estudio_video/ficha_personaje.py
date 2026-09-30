"""La ficha de cada personaje: nombre, carácter, la vuelta entera y las caras.

Una por persona, para mirarla y decidir. Es el documento que dice quién es cada
molde, y el que hay que revisar ANTES de rodar: cambiar un molde cuando ya hay
vídeos hechos deja los viejos y los nuevos sin casar.

    python ficha_personaje.py              todas
    python ficha_personaje.py --solo suri
"""
import argparse
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import elenco as E          # noqa: E402

CELDA = 168          # cada posición del giro
COLS = 12            # 24 posiciones en dos filas de doce
CARA = 190
MARGEN = 22
FONDO = (16, 13, 12)
TEXTO = (233, 228, 222)
TENUE = (154, 144, 138)


def ficha(clave: str) -> Path | None:
    p = B.ELENCO[clave]
    giro = E.giro_de(clave)
    caras = [f for f in E.vistas_de(clave, solo_cara=True)]
    if not giro and not caras:
        print(f"  {clave}: sin material")
        return None

    filas_giro = (len(giro) + COLS - 1) // COLS if giro else 0
    alto_giro = filas_giro * (int(CELDA * 1.5) + 20)
    ancho = COLS * CELDA + MARGEN * 2
    alto = MARGEN + 104 + alto_giro + (CARA + 34 if caras else 0) + MARGEN

    hoja = Image.new("RGB", (ancho, alto), FONDO)
    dib = ImageDraw.Draw(hoja)

    dib.text((MARGEN, MARGEN), p.nombre, fill=TEXTO)
    papel = {"sala": "camarero", "cliente": "cliente", "cocina": "cocina"}.get(p.papel, p.papel)
    dib.text((MARGEN, MARGEN + 16), f"{papel} · clave «{p.clave}» · semilla {p.semilla}",
             fill=TENUE)
    y = MARGEN + 38
    for linea in textwrap.wrap(p.personalidad, 150)[:3]:
        dib.text((MARGEN, y), linea, fill=TEXTO)
        y += 15
    dib.text((MARGEN, y + 4), f"Ropa: {p.vestuario}", fill=TENUE)

    y = MARGEN + 104
    alto_celda = int(CELDA * 1.5)
    for i, f in enumerate(giro):
        cx = MARGEN + (i % COLS) * CELDA
        cy = y + (i // COLS) * (alto_celda + 20)
        im = Image.open(f).convert("RGB").resize((CELDA - 6, alto_celda))
        hoja.paste(im, (cx, cy))
        dib.text((cx + 2, cy + alto_celda + 3), f"{E.GRADOS[i]}°", fill=TENUE)

    if caras:
        y2 = y + alto_giro + 6
        dib.text((MARGEN, y2 - 16), "Primeros planos", fill=TENUE)
        for i, f in enumerate(caras[:COLS]):
            im = Image.open(f).convert("RGB").resize((CARA, CARA))
            hoja.paste(im, (MARGEN + i * (CARA + 8), y2))

    destino = B.DIR_BIBLIA / "fichas" / f"{clave}.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    hoja.save(destino)
    print(f"  {p.nombre}: {len(giro)} posiciones, {len(caras)} caras → {destino.name}")
    return destino


def main() -> int:
    ap = argparse.ArgumentParser(description="La ficha de cada personaje")
    ap.add_argument("--solo", default="")
    args = ap.parse_args()
    claves = [c.strip() for c in args.solo.split(",") if c.strip()] or list(B.ELENCO)
    hechas = [f for c in claves if (f := ficha(c))]
    if not hechas:
        return 1
    print(f"\n{len(hechas)} fichas en {B.DIR_BIBLIA / 'fichas'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
