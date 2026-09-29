"""¿Acepta ComfyUI los grafos del estudio? Sin gastar GPU.

ComfyUI VALIDA el grafo entero al recibirlo: nombres de nodo, campos obligatorios,
tipos de cada enlace y que los ficheros elegidos existan. Si algo está mal,
contesta 400 y dice qué. Así que se encola y se retira de la cola en el acto: eso
comprueba todo lo que se puede comprobar sin ponerse a difundir.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402


def retirar(pid: str) -> None:
    cuerpo = json.dumps({"delete": [pid]}).encode()
    pet = urllib.request.Request(f"{C.COMFY}/queue", data=cuerpo,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(pet, timeout=15)
    except Exception:
        pass
    C.interrumpir()


def probar(nombre: str, grafo: dict) -> bool:
    try:
        pid = C.encolar(grafo)
    except C.ComfyCaido as e:
        print(f"  [RECHAZADO] {nombre}\n    {e}")
        return False
    print(f"  [aceptado]  {nombre}  (prompt_id {pid[:8]}…)")
    retirar(pid)
    return True


def main() -> int:
    if not C.encendido():
        print("ComfyUI no está arrancado")
        return 1

    libre, total = C.vram_libre()
    print(f"VRAM: {libre} MiB libres de {total}. Solo se valida, no se genera.\n")

    ok = True
    print("Grafo de casting (retrato del elenco):")
    ok &= probar("retrato de Nadia", E._grafo_retrato(B.ELENCO["nadia"]))

    print("\nGrafo de vídeo:")
    control = B.DIR_CONTROL / "comedor_profundidad.png"
    if not control.exists():
        print(f"  falta {control}; lanza `python estudio_cli.py camaras`")
        return 1

    ok &= probar("plano sin referencia de identidad", C.construir(
        prompt_positivo="two people eating at a table, " + B.ESTILO,
        prompt_negativo=B.ESTILO_NEGATIVO, control=control,
        fotogramas=32, semilla=1234, prefijo="validacion"))

    retrato = E.ruta_de("nadia")
    if retrato.exists():
        ok &= probar("plano CON referencia de identidad", C.construir(
            prompt_positivo="a veteran miner eating, " + B.ESTILO,
            prompt_negativo=B.ESTILO_NEGATIVO, control=control,
            fotogramas=32, semilla=1234, prefijo="validacion",
            referencia=retrato))
    else:
        print("  (el plano con IP-Adapter no se puede validar aún: no hay retratos)")

    print("\n" + ("Todo validado." if ok else "Hay grafos que ComfyUI no acepta."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
