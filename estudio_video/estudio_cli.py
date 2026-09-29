"""Punto de entrada del estudio, para la web y para la línea de órdenes.

    python estudio_cli.py web                     arranca la interfaz en :8099
    python estudio_cli.py salud                   qué hay encendido y qué falta
    python estudio_cli.py biblia                  relee el plano y la carta del KDS
    python estudio_cli.py camaras                 regenera los mapas de control
    python estudio_cli.py casting [--rehacer]     retrata al elenco (gasta GPU)
    python estudio_cli.py guion "un prompt"       escribe el guion y lo enseña
    python estudio_cli.py producir "un prompt"    hace el vídeo entero, aquí y ahora
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estudio import biblia as B          # noqa: E402
from estudio import comfy as C           # noqa: E402
from estudio import elenco as E          # noqa: E402
from estudio import geometria as G       # noqa: E402
from estudio import guion as Gu          # noqa: E402
from estudio import produccion as Pr     # noqa: E402
from estudio import voz as V             # noqa: E402
from estudio import web as W             # noqa: E402


def cmd_salud(_args) -> int:
    print("ComfyUI            :", "encendido" if C.encendido() else "APAGADO (Kinemato\\run.bat)")
    if C.encendido():
        libre, total = C.vram_libre()
        print(f"  VRAM             : {libre} MiB libres de {total}"
              f"{'  <-- no cabe un render' if libre < Pr.VRAM_MINIMA else ''}")
    print("Guionista          :", "modelo de lenguaje" if Gu.hay_llm() else "plantillas (sin LLM)")
    print("Voz (Piper/Raspa)  :", "sí" if V.disponible() else "no")
    falta = E.falta_casting()
    print("Casting            :", "completo" if not falta else f"faltan {', '.join(falta)}")
    try:
        bib = B.cargar()
        print(f"Biblia             : {len(bib.plano)} elementos de plano, {len(bib.mesas)} mesas, "
              f"{len(bib.platos)} platos")
    except Exception as e:
        print("Biblia             : ERROR", e)
    hechos = [c for c in B.CAMARAS if (B.DIR_CONTROL / f"{c}_profundidad.png").exists()]
    print(f"Mapas de cámara    : {len(hechos)} de {len(B.CAMARAS)}")
    return 0


def cmd_biblia(_args) -> int:
    bib = B.descargar()
    print(f"plano: {len(bib.plano)} elementos ({len(bib.mesas)} mesas)")
    print(f"carta: {len(bib.platos)} platos")
    G.generar_controles(bib)
    print(f"mapas de control regenerados en {B.DIR_CONTROL}")
    return 0


def cmd_camaras(_args) -> int:
    for clave, d in G.generar_controles().items():
        print(f"  {clave:10s} {d['metros_cerca']}–{d['metros_lejos']} m  {d['camara']}")
    return 0


def cmd_casting(args) -> int:
    solo = [c.strip() for c in (args.solo or "").split(",") if c.strip()] or None
    for clave, r in E.casting(rehacer=args.rehacer, solo=solo).items():
        print(f"  {clave:8s} {r}")
    return 0


def cmd_hojas(args) -> int:
    solo = [c.strip() for c in (args.solo or "").split(",") if c.strip()] or None
    for clave, r in E.hojas(rehacer=args.rehacer, solo=solo).items():
        print(f"  {clave:8s} {r}")
    return 0


def cmd_guion(args) -> int:
    g = Gu.escribir(args.prompt, usar_llm=not args.sin_llm)
    print(json.dumps(g.a_dict(), ensure_ascii=False, indent=1))
    return 0


def cmd_producir(args) -> int:
    t = Pr.Trabajo(Pr._nuevo_id())
    try:
        estado = Pr.producir(args.prompt, t, usar_llm=not args.sin_llm, con_voz=not args.sin_voz)
    except Exception as e:
        print(f"FALLÓ: {e}")
        return 1
    print(f"\nlisto: {Pr.DIR_SALIDAS / estado['salida']}")
    for a in estado["avisos"]:
        print(f"  aviso: {a}")
    return 0


def cmd_publicar(args) -> int:
    from estudio import publicar as Pub
    try:
        url = Pub.publicar(Pr.DIR_SALIDAS, solo=[s.strip() for s in args.solo.split(",")
                                                 if s.strip()] or None)
    except Exception as e:
        print(f"FALLÓ: {e}")
        return 1
    print(f"publicado (solo LAN): {url}")
    return 0


def cmd_web(args) -> int:
    W.servir(args.puerto)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Estudio de vídeo del KDS+TPV")
    sub = p.add_subparsers(dest="orden", required=True)

    sub.add_parser("salud").set_defaults(func=cmd_salud)
    sub.add_parser("biblia").set_defaults(func=cmd_biblia)
    sub.add_parser("camaras").set_defaults(func=cmd_camaras)

    c = sub.add_parser("casting")
    c.add_argument("--rehacer", action="store_true", help="vuelve a retratar aunque ya exista")
    c.add_argument("--solo", default="", help="claves separadas por comas")
    c.set_defaults(func=cmd_casting)

    h = sub.add_parser("hojas", help="la hoja de personaje de cada molde (varias vistas)")
    h.add_argument("--rehacer", action="store_true")
    h.add_argument("--solo", default="", help="claves separadas por comas")
    h.set_defaults(func=cmd_hojas)

    g = sub.add_parser("guion")
    g.add_argument("prompt")
    g.add_argument("--sin-llm", action="store_true")
    g.set_defaults(func=cmd_guion)

    pr = sub.add_parser("producir")
    pr.add_argument("prompt")
    pr.add_argument("--sin-llm", action="store_true")
    pr.add_argument("--sin-voz", action="store_true")
    pr.set_defaults(func=cmd_producir)

    pu = sub.add_parser("publicar", help="subir los vídeos a home.pr1.es/videos (solo LAN)")
    pu.add_argument("--solo", default="", help="nombres de fichero separados por comas")
    pu.set_defaults(func=cmd_publicar)

    w = sub.add_parser("web")
    w.add_argument("--puerto", type=int, default=W.PUERTO)
    w.set_defaults(func=cmd_web)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
