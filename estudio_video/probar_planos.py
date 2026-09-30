"""Rueda SOLO los planos generados de video_servicio.py, como imagen, sin montar.

Sirve para mirar antes de gastar el vídeo entero. Monta el prompt EXACTAMENTE
como produccion.py (mismo orden, mismos pesos, misma semilla por índice), así que
lo que sale aquí es lo que va a salir allí.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402
from estudio import produccion as Pr     # noqa: E402
import video_servicio as VS              # noqa: E402

SOLO = [int(x) for x in sys.argv[1:]] or None      # números de plano, 1..12


def main() -> int:
    g = VS.guion()
    for i, esc in enumerate(g.escenas):
        if esc.pantalla:
            continue
        if SOLO and (i + 1) not in SOLO:
            continue

        positivo = Pr.prompt_de(esc)       # el MISMO que usa producción
        semilla = esc.semilla(B.FORMATO["semilla_base"], i)
        grafo = C.construir_fijo(
            prompt_positivo=positivo, prompt_negativo=Pr.negativo_de(esc),
            control=B.DIR_CONTROL / f"{esc.camara}_profundidad.png",
            semilla=semilla, prefijo=f"planos_{i+1:02d}_{esc.camara}",
            referencia=E.referencia_para(esc.personajes),
            cuerpo=E.cuerpo_de(esc.personajes[0]) if esc.personajes else None)
        pid = C.encolar(grafo)
        salidas = C.esperar(pid, aviso=lambda s, e, n=i + 1: print(f"   {n}: {e}, {s} s"))
        img = [s for s in salidas if s.suffix.lower() == ".png"]
        print(f"plano {i+1:2d} {esc.camara:8s} {'+'.join(esc.personajes) or '-':8s} "
              f"-> {img[0].name if img else 'SIN IMAGEN'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
