"""Prueba de moldes: las MISMAS cuatro acciones, una detrás de otra, para cada molde.

Es la forma de ver si el elenco aguanta. Con la misma acción, la misma cámara y la
misma semilla para todos, lo único que cambia de un bloque al siguiente es la
persona: si alguien no se parece a su retrato, o si dos moldes salen pareciéndose
entre ellos, se ve de un vistazo comparando la misma acción en dos bloques.

    python prueba_moldes.py                 los cinco moldes, cuatro acciones
    python prueba_moldes.py --solo oliver,teo
    python prueba_moldes.py --segundos 4    planos más largos (y más cómputo)
"""
import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import elenco as E          # noqa: E402
from estudio import guion as Gu          # noqa: E402
from estudio import produccion as Pr     # noqa: E402

# La lista, idéntica para todos. Cada acción con su cámara fija: comparar dos
# moldes solo tiene sentido si están grabados desde el mismo sitio.
ACCIONES = [
    ("entrada", "Entra por la puerta",
     "walks in through the doorway, stops and looks around the room"),
    ("comedor", "Cruza el comedor",
     "walks between the tables, glancing to one side"),
    ("mesa", "Pide desde el móvil",
     "sits at the table, holds up a phone in one hand and taps it, looking down at it"),
    ("atraque", "Paga en la barra",
     "stands at the counter, holds a phone towards the counter edge and then looks up"),
]


def guion_de(claves: list[str], segundos: int, cuantas: int = 0) -> Gu.Guion:
    escenas = []
    acciones = ACCIONES[:cuantas] if cuantas else ACCIONES
    for clave in claves:
        p = B.ELENCO[clave]
        for i, (camara, titulo, accion) in enumerate(acciones, start=1):
            escenas.append(Gu.Escena(
                camara=camara,
                accion=f"{p.breve} {accion}",
                narracion="",                      # es una prueba, no un vídeo narrado
                personajes=[clave],
                segundos=segundos,
                rotulo=f"{p.nombre} · {i} de 4 — {titulo}",
            ))
    return Gu.Guion(titulo="Prueba de moldes", tipo="escena", escenas=escenas,
                    prompt="prueba de moldes: las mismas cuatro acciones para cada molde")


def main() -> int:
    p = argparse.ArgumentParser(description="Las mismas cuatro acciones para cada molde")
    p.add_argument("--solo", default="", help="claves separadas por comas")
    p.add_argument("--segundos", type=int, default=3)
    p.add_argument("--acciones", type=int, default=0,
                   help="usar solo las N primeras acciones (para iterar barato)")
    args = p.parse_args()

    claves = [c.strip() for c in args.solo.split(",") if c.strip()] or list(B.ELENCO)
    malas = [c for c in claves if c not in B.ELENCO]
    if malas:
        print(f"no están en el elenco: {', '.join(malas)}")
        return 1

    sin_retrato = [c for c in claves if not E.ruta_de(c).exists()]
    if sin_retrato:
        print(f"sin retrato: {', '.join(sin_retrato)}. Lanza `python estudio_cli.py casting`.")
        return 1

    g = guion_de(claves, args.segundos, args.acciones)
    print(f"{len(claves)} moldes x {args.acciones or len(ACCIONES)} acciones = "
          f"{len(g.escenas)} planos, {g.segundos} s de vídeo")
    print("En una 1080 Ti esto son unos 35-45 minutos de cómputo.\n")

    t = Pr.Trabajo(Pr._nuevo_id())
    try:
        estado = Pr.producir(g.prompt, t, con_voz=False, guion_hecho=g)
    except Exception as e:
        print(f"FALLÓ: {e}")
        return 1
    print(f"\nlisto: {Pr.DIR_SALIDAS / estado['salida']}")
    for a in estado["avisos"]:
        print(f"  aviso: {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
