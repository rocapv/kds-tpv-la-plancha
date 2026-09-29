"""Vigilante: espera a que la GPU quede libre y hace la primera tirada.

En Pecera la tarjeta se comparte con los relatos de la bitácora, los cursos de la
academia y el pipeline de Star Citizen, y LM Studio carga en ella modelos de 7 GB.
Este vigilante mira cada pocos minutos y, en cuanto cabe un render, hace por su
cuenta lo que hay que hacer una vez: el **casting** de los nueve retratos y un
**clip de prueba**.

No le quita la tarjeta a nadie. Si un modelo de LM Studio se queda cargado pero
ocioso, lo dice en el registro y sigue esperando: descargarlo tendría un efecto
que no le toca decidir a un vigilante, porque el JIT lo recargaría con el contexto
por defecto (4.096) y le rompería la ventana a quien lo estuviera usando.

    python esperar_gpu.py                      espera hasta 12 h, mirando cada 3 min
    python esperar_gpu.py --horas 2 --cada 60
    python esperar_gpu.py --solo-avisar        no genera nada, solo vigila y anota
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402
from estudio import produccion as Pr     # noqa: E402

REGISTRO = AQUI / "trabajos" / "_vigilante.log"
PRUEBA = ("Un plano del comedor: dos clientes comiendo mientras la camarera "
          "pasa entre las mesas con una bandeja")


def anotar(texto: str) -> None:
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {texto}"
    print(linea, flush=True)
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def modelos_cargados() -> list[str]:
    try:
        r = subprocess.run([str(Path.home() / ".lmstudio" / "bin" / "lms.exe"), "ps"],
                           capture_output=True, text=True, timeout=25)
        return [l for l in (r.stdout or "").splitlines()
                if l.strip() and not l.startswith("IDENTIFIER")]
    except Exception:
        return []


def main() -> int:
    p = argparse.ArgumentParser(description="Espera a que la GPU se libere y hace la primera tirada")
    p.add_argument("--horas", type=float, default=12.0)
    p.add_argument("--cada", type=int, default=180, help="segundos entre comprobaciones")
    p.add_argument("--solo-avisar", action="store_true")
    args = p.parse_args()

    limite = time.time() + args.horas * 3600
    anotar(f"vigilante en marcha: hasta {args.horas} h, mirando cada {args.cada} s "
           f"(hacen falta {Pr.VRAM_MINIMA} MiB)")

    seguidas = 0
    ultimo_aviso = ""
    while time.time() < limite:
        if not C.encendido():
            anotar("ComfyUI no responde; sigo esperando")
            time.sleep(args.cada)
            continue

        libre, total = C.vram_libre()
        if libre >= Pr.VRAM_MINIMA:
            seguidas += 1
            # Dos lecturas seguidas: que no entre por un hueco de un instante,
            # justo entre dos peticiones de otro proceso.
            anotar(f"{libre} MiB libres ({seguidas}/2)")
            if seguidas >= 2:
                break
        else:
            seguidas = 0
            cargados = modelos_cargados()
            aviso = f"{libre} de {total} MiB libres"
            if cargados:
                aviso += " | LM Studio: " + "; ".join(c.split()[0] + " " + c.split()[2]
                                                      for c in cargados if len(c.split()) > 2)
            if aviso != ultimo_aviso:          # no repetir la misma línea cada tres minutos
                anotar(aviso)
                ultimo_aviso = aviso
        time.sleep(args.cada)
    else:
        anotar("se acabó el tiempo de espera y la tarjeta no se ha liberado. "
               "Si el modelo de LM Studio está IDLE, ocupa memoria sin usarla: "
               "`lms unload <identificador>` la devuelve, pero corta a quien lo tuviera cargado.")
        return 2

    anotar(f"GPU libre. Casting de {len(E.falta_casting())} retratos")
    if args.solo_avisar:
        anotar("--solo-avisar: no genero nada")
        return 0

    for clave, r in E.casting().items():
        anotar(f"  {clave}: {r}")

    anotar("clip de prueba")
    t = Pr.Trabajo(Pr._nuevo_id())
    try:
        estado = Pr.producir(PRUEBA, t, usar_llm=False, con_voz=True)
        anotar(f"listo: {Pr.DIR_SALIDAS / estado['salida']}")
        for a in estado["avisos"]:
            anotar(f"  aviso: {a}")
    except Exception as e:
        anotar(f"FALLÓ: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
