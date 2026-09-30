"""Rueda VARIAS TOMAS de un mismo plano para poder elegir.

    python probar_tomas.py 2 0 1 2 3
    python probar_tomas.py --guion video_mesa 1 0 1 2 3

Primero el número de plano, después los números de toma. Monta el prompt con
`produccion.prompt_de` y `produccion.negativo_de`, igual que el rodaje de verdad,
así que la toma que se elija aquí es la que saldrá luego poniendo `toma=N` en
la escena del guion.

`--guion` dice de qué fichero salen las escenas; por defecto `video_servicio`,
que era el único que había cuando se escribió esto. Vale cualquier módulo con
una función `guion()`.
"""
import importlib
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402
from estudio import produccion as Pr     # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    modulo = "video_servicio"
    if args and args[0] == "--guion":
        modulo, args = args[1], args[2:]
    plano = int(args[0])
    tomas = [int(x) for x in args[1:]] or [0, 1, 2, 3]
    i = plano - 1
    esc = importlib.import_module(modulo).guion().escenas[i]

    for t in tomas:
        esc.toma = t
        grafo = C.construir_fijo(
            prompt_positivo=Pr.prompt_de(esc), prompt_negativo=Pr.negativo_de(esc),
            control=B.DIR_CONTROL / f"{esc.camara}_profundidad.png",
            semilla=esc.semilla(B.FORMATO["semilla_base"], i),
            prefijo=f"toma_{plano:02d}_{t}",
            referencia=E.referencia_para(esc.personajes),
            cuerpo=E.cuerpo_de(esc.personajes[0]) if esc.personajes else None)
        C.esperar(C.encolar(grafo))
        print(f"plano {plano} toma {t}: listo  ({esc.camara}, semilla "
              f"{esc.semilla(B.FORMATO['semilla_base'], i)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
