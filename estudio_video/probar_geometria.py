"""Prueba de la primera pieza: ¿sale la cantina de verdad del plano de verdad?

Baja el plano y la carta, genera los mapas de control de las nueve cámaras y
además deja una hoja de contactos para mirarlas todas de un vistazo. Si esta
hoja está bien, la sala de todos los vídeos está bien.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estudio import biblia as B          # noqa: E402
from estudio import geometria as G       # noqa: E402


def main() -> int:
    print("==> bajando plano y carta del KDS")
    try:
        bib = B.descargar()
    except Exception as e:
        print(f"    no se pudo bajar ({e}); se usa la copia guardada")
        bib = B.cargar()
    print(f"    plano: {len(bib.plano)} elementos, {len(bib.mesas)} mesas")
    print(f"    carta: {len(bib.platos)} platos disponibles")
    print(f"    local: {bib.local.get('local_nombre', '(sin nombre)')}")

    print("==> generando mapas de control (9 cámaras)")
    hecho = G.generar_controles(bib, ancho=512, alto=288)
    for clave, d in hecho.items():
        print(f"    {clave:10s} {d['cobertura']*100:5.1f}% de la imagen "
              f"| {d['metros_cerca']}–{d['metros_lejos']} m | {d['camara']}")

    # Hoja de contactos: 3x3 con la profundidad y las líneas superpuestas en rojo.
    cols, filas, w, h, margen = 3, 3, 512, 288, 24
    hoja = Image.new("RGB", (cols * w + margen * 4, filas * (h + 22) + margen * 4), (12, 12, 14))
    dib = ImageDraw.Draw(hoja)
    for i, (clave, d) in enumerate(hecho.items()):
        prof = Image.open(d["profundidad"]).convert("RGB")
        lin = Image.open(d["lineas"])
        rojo = Image.new("RGB", prof.size, (255, 70, 70))
        prof.paste(rojo, (0, 0), lin)
        x = margen + (i % cols) * (w + margen // 2)
        y = margen + (i // cols) * (h + 22 + margen // 2)
        hoja.paste(prof, (x, y))
        dib.text((x + 2, y + h + 4), f"{clave} — {B.CAMARAS[clave].nombre}", fill=(210, 210, 215))

    salida = B.DIR_BIBLIA / "contactos_camaras.png"
    hoja.save(salida)
    print(f"==> hoja de contactos: {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
