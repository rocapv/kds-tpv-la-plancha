"""La hoja del elenco: los moldes juntos, para mirarlos de una vez.

Son las caras que van a salir en todos los vídeos. Verlas en fila es la forma
rápida de decidir si un molde no vale, porque una vez empiezan a rodar, cambiar
uno significa que los vídeos viejos y los nuevos ya no casan.

    python hoja_elenco.py              una fila con los cinco retratos base
    python hoja_elenco.py --hojas      la hoja de personaje entera de cada uno
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import elenco as E          # noqa: E402

LADO = 320
PIE = 46
LADO_VISTA = 200


def hojas_de_personaje() -> int:
    """Una fila por persona, con todas sus vistas: la guía de referencia."""
    gente = [p for p in B.ELENCO.values() if E.vistas_de(p.clave, solo_cara=False)]
    if not gente:
        print("no hay hojas: `python estudio_cli.py hojas`")
        return 1

    nombres = [v for v, _, _ in E.VISTAS]
    ancho = LADO_VISTA * len(nombres) + 14 * (len(nombres) + 1)
    alto_fila = LADO_VISTA + 40
    hoja = Image.new("RGB", (ancho, alto_fila * len(gente) + 28), (16, 13, 12))
    dib = ImageDraw.Draw(hoja)

    for f, p in enumerate(gente):
        y = 14 + f * alto_fila
        dib.text((16, y - 2), f"{p.nombre}  ·  {p.papel}", fill=(233, 228, 222))
        vistas = {v.stem: v for v in E.vistas_de(p.clave, solo_cara=False)}
        vistas["frontal"] = E.ruta_de(p.clave)
        for c, nombre in enumerate(nombres):
            x = 14 + c * (LADO_VISTA + 14)
            ruta = vistas.get(nombre)
            if ruta and ruta.exists():
                img = Image.open(ruta).convert("RGB").resize((LADO_VISTA, LADO_VISTA))
                hoja.paste(img, (x, y + 16))
            dib.text((x, y + LADO_VISTA + 20), nombre.replace("_", " "), fill=(154, 144, 138))

    salida = B.DIR_BIBLIA / "hojas_personaje.png"
    hoja.save(salida)
    print(salida)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Los moldes, para mirarlos")
    ap.add_argument("--hojas", action="store_true",
                    help="la hoja de personaje entera de cada molde")
    if ap.parse_args().hojas:
        return hojas_de_personaje()

    gente = [p for p in B.ELENCO.values() if E.ruta_de(p.clave).exists()]
    if not gente:
        print("no hay retratos: `python estudio_cli.py casting`")
        return 1

    ancho = LADO * len(gente) + 16 * (len(gente) + 1)
    hoja = Image.new("RGB", (ancho, LADO + PIE + 32), (16, 13, 12))
    dib = ImageDraw.Draw(hoja)

    for i, p in enumerate(gente):
        x = 16 + i * (LADO + 16)
        cara = Image.open(E.ruta_de(p.clave)).convert("RGB").resize((LADO, LADO))
        hoja.paste(cara, (x, 16))
        papel = {"sala": "camarero", "cliente": "cliente", "cocina": "cocina"}.get(p.papel, p.papel)
        dib.text((x, LADO + 26), p.nombre, fill=(233, 228, 222))
        dib.text((x, LADO + 42), f"{papel} · clave «{p.clave}» · semilla {p.semilla}",
                 fill=(154, 144, 138))

    salida = B.DIR_BIBLIA / "hoja_elenco.png"
    hoja.save(salida)
    print(salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
