"""Prueba del grafo DE PRODUCCIÓN, que no es el de `probar_fijo.py`.

`probar_fijo.py` monta su propio grafo, más simple: no engancha el IP-Adapter de
vestuario. Por eso se pudo ajustar el estudio con él y que la producción siguiera
sacando caras manchadas de naranja: lo que se estaba midiendo no era lo que luego
se ejecutaba. Esta prueba llama a `comfy.construir_fijo`, el mismo que usa
`produccion.py`, y barre las dos fuerzas que importan.

    python probar_produccion.py --camara entrada --quien nadia \
        --accion "walks in through the doorway, looking around the room"
"""
import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402

# (nombre, fuerza_control, con_vestuario)
VARIANTES = [
    ("a_actual_c30_ropa", 0.30, True),
    ("b_c55_ropa", 0.55, True),
    ("c_c55_sin_ropa", 0.55, False),
    ("d_c70_sin_ropa", 0.70, False),
]


def main() -> int:
    p = argparse.ArgumentParser(description="Barrido sobre el grafo de producción")
    p.add_argument("--camara", default="entrada")
    p.add_argument("--quien", default="nadia")
    p.add_argument("--accion", default="walks in through the doorway, looking around the room")
    p.add_argument("--semilla", type=int, default=90210)
    args = p.parse_args()

    per = B.ELENCO[args.quien]
    control = B.DIR_CONTROL / f"{args.camara}_profundidad.png"
    referencia = E.referencia_para([args.quien])
    cuerpo = E.cuerpo_de(args.quien)

    # El mismo orden de prompt que produccion.py
    positivo = ", ".join(x for x in [
        f"({per.breve}:1.3)",
        f"({per.vestuario}:1.2)" if per.vestuario else "",
        args.accion, B.ESTILO] if x)
    print(positivo, "\n")

    for nombre, fuerza, con_ropa in VARIANTES:
        grafo = C.construir_fijo(
            prompt_positivo=positivo, prompt_negativo=B.ESTILO_NEGATIVO,
            control=control, semilla=args.semilla,
            prefijo=f"probar_{args.camara}_{nombre}",
            referencia=referencia, cuerpo=cuerpo if con_ropa else None,
            fuerza_control=fuerza)
        pid = C.encolar(grafo)
        salidas = C.esperar(pid, aviso=lambda s, e, n=nombre: print(f"  {n}: {e}, {s} s"))
        img = [s for s in salidas if s.suffix.lower() == ".png"]
        print(f"{nombre:22s} control={fuerza:.2f} ropa={'si' if con_ropa else 'no':3s} "
              f"-> {img[0].name if img else 'SIN IMAGEN'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
