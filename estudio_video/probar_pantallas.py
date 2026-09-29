"""Prueba de la grabación de pantallas: ¿responde el KDS y salen las burbujas?

No genera nada con GPU. Comprueba que las pantallas contestan, graba dos (una
pública y una con PIN) y deja los webm para mirarlos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estudio import pantallas as P     # noqa: E402


def main() -> int:
    print("==> ¿responden las pantallas del sitio de pruebas?")
    for clave, estado in P.comprobar().items():
        print(f"    {clave:10s} {estado}")

    destino = Path(__file__).resolve().parent / "trabajos" / "_prueba"
    for clave, segundos in (("cliente", 6), ("kds", 10), ("tpv", 10)):
        print(f"==> grabando «{clave}» {segundos} s")
        try:
            w = P.grabar(clave, segundos=segundos, destino=destino,
                         avisar=lambda t: print(f"    aviso: {t}"))
            print(f"    {w}  ({w.stat().st_size // 1024} KiB)")
        except Exception as e:
            print(f"    FALLÓ: {type(e).__name__}: {e}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
