"""Graba unas pantallas y saca tres fotogramas de cada clip: principio, medio y fin.

    python probar_pantallas.py tpv sala kds
    python probar_pantallas.py tpv:cobrar        con gesto, tras los dos puntos

Los tres fotogramas son los tres sitios donde se esconden los fallos de este
módulo, y ninguno de los tres da error:

  · **el principio** dice si el clip empieza en la pantalla o en el teclado del
    PIN, que es lo que pasaba antes de `_sesion_previa`;
  · **el medio** dice si la pantalla se pintó entera o se quedó a oscuras porque
    el escaparate devolvió una forma que el JavaScript no esperaba;
  · **el final** es lo que se ve de verdad en un plano con gesto, porque es por
    donde corta el montaje.

Mirarlos a ojo es el único control que hay: un clip mal grabado pesa lo mismo y
dura lo mismo que uno bueno.
"""
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import montaje as M       # noqa: E402
from estudio import pantallas as P     # noqa: E402


def main() -> int:
    claves = sys.argv[1:] or ["tpv", "sala"]
    dest = AQUI / "trabajos" / "_pant"
    for clave in claves:
        gesto = None
        if ":" in clave:
            clave, gesto = clave.split(":", 1)
        d = dest / (clave + (f"_{gesto}" if gesto else ""))
        w = P.grabar(clave, segundos=6, con_tutorial=False, destino=d, gesto=gesto,
                     avisar=lambda m: print(f"  aviso: {m}"))
        clave = clave + (f"_{gesto}" if gesto else "")
        dur = M.duracion(w)
        print(f"{clave}: {w.name}  {dur:.2f}s")
        for t in (0.3, dur / 2, max(0.0, dur - 0.5)):
            salida = dest / f"{clave}_{t:04.1f}.jpg"
            subprocess.run([M.ffmpeg(), "-y", "-ss", f"{t}", "-i", str(w),
                            "-frames:v", "1", "-q:v", "3", str(salida)],
                           capture_output=True)
            print(f"   {salida.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
