"""Rehacer el montaje de un trabajo SIN volver a generar nada.

Las imágenes de un trabajo cuestan minutos de GPU; los rótulos, el movimiento de
cámara y los fundidos cuestan segundos de ffmpeg. Cuando lo que falla es el
montaje —y ha fallado: los planos salieron durando seis minutos y medio por un
`-loop` de más—, rehacer también las imágenes es tirar el trabajo caro por un
fallo del barato.

    python remontar.py                 el último trabajo
    python remontar.py 20260929_203509
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import montaje as M         # noqa: E402
from estudio import produccion as Pr     # noqa: E402
from estudio import publicar as Pub      # noqa: E402
from estudio import voz as V             # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Rehace el montaje sin regenerar imágenes")
    p.add_argument("trabajo", nargs="?", default="")
    p.add_argument("--sin-publicar", action="store_true")
    args = p.parse_args()

    ident = args.trabajo
    if not ident:
        hechos = sorted((d.name for d in Pr.DIR_TRABAJOS.iterdir()
                         if d.is_dir() and not d.name.startswith("_")), reverse=True)
        if not hechos:
            print("no hay trabajos")
            return 1
        ident = hechos[0]

    dir_trabajo = Pr.DIR_TRABAJOS / ident
    guion = dir_trabajo / "guion.json"
    if not guion.exists():
        print(f"no hay guion en {dir_trabajo}")
        return 1
    g = json.loads(guion.read_text(encoding="utf-8"))
    escenas = g["escenas"]
    print(f"{ident}: {len(escenas)} planos · {g['titulo']}")

    bib = B.cargar()
    marca = bib.local.get("local_nombre") or "Cantina Vesta-9"

    # Las imágenes generadas siguen donde las dejó ComfyUI, con el prefijo del
    # trabajo: se recuperan por nombre en vez de volver a pedirlas.
    salidas_comfy = sorted(B.DIR_COMFY_SALIDAS.glob(f"kds_{ident}_*"))
    por_plano: dict[int, Path] = {}
    for f in salidas_comfy:
        if f.suffix.lower() not in (".png", ".jpg", ".mp4"):
            continue
        trozo = f.stem.split("_")
        try:
            por_plano.setdefault(int(trozo[3]), f)
        except (IndexError, ValueError):
            continue

    normalizados, audios, tramos = [], [], []
    reloj = 0.0
    for i, e in enumerate(escenas):
        fuente = por_plano.get(i)
        if fuente is None:
            crudo = dir_trabajo / "crudos" / f"{e.get('pantalla') or ''}.webm"
            fuente = crudo if crudo.exists() else None
        if fuente is None:
            print(f"  plano {i+1}: sin material, se salta")
            continue

        segundos = float(e["segundos"])
        wav = dir_trabajo / "voz" / f"{i:02d}.wav"
        if wav.exists():
            segundos = max(segundos, V.duracion(wav) + 0.6)

        destino = dir_trabajo / "planos" / f"{i:02d}.mp4"
        try:
            if fuente.suffix.lower() in (".png", ".jpg"):
                mov = M.movimiento_de(i, e["camara"])
                normalizados.append(M.desde_imagen(fuente, destino, segundos, movimiento=mov,
                                                   rotulo=e.get("rotulo", ""), marca=marca))
            else:
                normalizados.append(M.normalizar(fuente, destino, segundos,
                                                 rotulo=e.get("rotulo", ""), marca=marca))
        except Exception as ex:
            print(f"  plano {i+1}: {ex}")
            continue
        audios.append(M.pista_de_voz(wav if wav.exists() else None, segundos,
                                     dir_trabajo / "audio" / f"{i:02d}.wav"))
        if e.get("narracion"):
            tramos.append((reloj, reloj + segundos, e["narracion"]))
        reloj += segundos
        print(f"  plano {i+1}/{len(escenas)} · {segundos:.1f} s")

    if not normalizados:
        print("no quedó nada que montar")
        return 1

    srt = V.subtitulos(tramos, dir_trabajo / "subtitulos.srt") if tramos else None
    estado = Pr.Trabajo.cargar(ident) or {}
    nombre = estado.get("salida") or f"{ident}_{Pr._limpiar(g['titulo'])}.mp4"
    final = Pr.DIR_SALIDAS / nombre
    M.unir(normalizados, audios, final, srt)
    try:
        M.portada(final, Pr.DIR_SALIDAS / (final.stem + ".jpg"))
    except Exception:
        pass
    if srt:
        shutil.copy2(srt, Pr.DIR_SALIDAS / (final.stem + ".srt"))

    print(f"\nlisto: {final}  ({reloj:.0f} s)")
    if not args.sin_publicar:
        try:
            print("publicado:", Pub.publicar(Pr.DIR_SALIDAS, solo=[final.name]))
        except Exception as e:
            print(f"no se publicó: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
