"""Rueda un plano ANIMADO con varias fuerzas de ControlNet, para poder elegir.

    python probar_profundidad.py --guion video_mesa 1 0.30:0.60 0.45:0.85 0.60:0.95

Cada argumento después del número de plano es `fuerza:hasta`. Sale un clip por
combinación, y lo que hay que mirar en cada uno es el ÚLTIMO fotograma, no el
primero: el fallo de este modo no es que empiece mal, es que se deshace.

Por qué existe esto y no se toca la constante a ojo: en imagen fija está medido
que subir la fuerza encoge a la persona hasta borrarla (0,60 → «no hay persona,
solo muebles», `comfy.py`). En animado el fallo es el contrario —la geometría se
suelta a lo largo del clip— así que el número bueno no tiene por qué ser el
mismo, pero tampoco se puede dar por hecho que subirlo arregle nada. Se mide.

Los clips salen cortos a propósito (`--segundos`, 2 por defecto): lo que se
compara es si la persona sigue ahí al final, y eso se ve igual en 16 fotogramas
que en 32, por la mitad de GPU.
"""
import argparse
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
    p = argparse.ArgumentParser(description="Barrido de fuerza de profundidad en animado")
    p.add_argument("--guion", default="video_servicio")
    p.add_argument("--segundos", type=int, default=2)
    p.add_argument("plano", type=int)
    p.add_argument("combinaciones", nargs="+", help="fuerza:hasta, p.ej. 0.45:0.85")
    args = p.parse_args()

    i = args.plano - 1
    esc = importlib.import_module(args.guion).guion().escenas[i]
    if esc.pantalla:
        print(f"el plano {args.plano} es una pantalla grabada, no se genera")
        return 1

    fotogramas = max(16, args.segundos * B.FORMATO["fps"])
    for combo in args.combinaciones:
        fuerza, hasta = (float(x) for x in combo.split(":"))
        grafo = C.construir(
            prompt_positivo=Pr.prompt_de(esc), prompt_negativo=Pr.negativo_de(esc),
            control=B.DIR_CONTROL / f"{esc.camara}_profundidad.png",
            fotogramas=fotogramas, semilla=esc.semilla(B.FORMATO["semilla_base"], i),
            prefijo=f"prof_{args.plano:02d}_{fuerza:.2f}_{hasta:.2f}".replace(".", ""),
            referencia=E.referencia_para(esc.personajes),
            cuerpo=E.cuerpo_de(esc.personajes[0]) if esc.personajes else None,
            fuerza_control=fuerza)
        # `end_percent` no es parámetro de `construir`: se ajusta en el grafo ya
        # montado, que es más honesto que añadir un argumento solo para la prueba.
        grafo["12"]["inputs"]["end_percent"] = hasta
        C.esperar(C.encolar(grafo))
        print(f"plano {args.plano}  fuerza {fuerza:.2f}  hasta {hasta:.2f}: listo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
