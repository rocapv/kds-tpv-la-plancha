"""La hoja del elenco: los moldes juntos, para mirarlos de una vez.

Son las caras que van a salir en todos los vídeos. Verlas en fila es la forma
rápida de decidir si un molde no vale, porque una vez empiezan a rodar, cambiar
uno significa que los vídeos viejos y los nuevos ya no casan.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import elenco as E          # noqa: E402

LADO = 320
PIE = 46


def main() -> int:
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
