"""¿De verdad los bots van a rachas y sin atascarse? Se mide, no se supone.

    python qa_ritmo.py --url https://home.pr1.es --minutos 7

Arranca la simulación, toma una muestra cada 15 s durante dos ciclos completos de marcha y al
final responde a tres preguntas:

  1. ¿Hay rachas? (que las marchas cambien a lo largo del rato, no un ritmo plano)
  2. ¿Van desacompasados? (que en ningún momento el equipo entero vaya a la misma marcha)
  3. ¿Se atasca la cocina? (que la cola de comandas no crezca sin parar)

Deja la simulación EN PAUSA al terminar y no borra nada: lo que haya creado se queda para la
demo, y se limpia cuando se quiera con el botón ⟲ de la barra.
"""
import argparse
import json
import sys
import time
import urllib.request

fallos = []


def mal(t):
    fallos.append(t); print("  ✗ " + t)


def bien(t):
    print("  · " + t)


class Api:
    def __init__(self, url, pin="9999"):
        self.url = url.rstrip("/")
        self.token = self._pide("/api/login", {"pin": pin})["token"]

    def _pide(self, ruta, cuerpo=None, metodo=None):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(self.url + ruta, data=datos,
                                     method=metodo or ("POST" if datos else "GET"))
        req.add_header("Content-Type", "application/json")
        if getattr(self, "token", None):
            req.add_header("Authorization", "Bearer " + self.token)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    get = _pide

    def post(self, ruta):
        return self._pide(ruta, {}, "POST")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://home.pr1.es")
    ap.add_argument("--minutos", type=float, default=7.0)
    ap.add_argument("--cada", type=int, default=15)
    a = ap.parse_args()

    api = Api(a.url)
    print(f"1 · arrancando la simulación en {a.url}")
    estado = api.post("/api/simulacion/play")
    ciclo = estado.get("ciclo_marcha", 180)
    print(f"  · {len(estado['bots'])} bots · marcha cada {ciclo:.0f} s")

    muestras = []
    fin = time.time() + a.minutos * 60
    print(f"2 · midiendo {a.minutos:.0f} min (muestra cada {a.cada} s)")
    print(f"     {'mm:ss':>6}  {'cola':>5} {'espera':>6}  marchas                 pedidos cobrados")
    t0 = time.time()
    while time.time() < fin:
        s = api.get("/api/simulacion")
        k = api.get("/api/kds?limite=1")
        cola = len(k["comandas"]) + k.get("esperando", 0)
        m = s.get("marchas", {})
        muestras.append({"t": round(time.time() - t0), "cola": cola, "marchas": m,
                         "pedidos": s["pedidos"], "cobrados": s["cobrados"],
                         "abiertos": s["pedidos"] - s["cobrados"],
                         "por_bot": {b["area"]: b.get("marcha") for b in s["bots"]}})
        seg = int(time.time() - t0)
        print(f"     {seg // 60:02d}:{seg % 60:02d}  {cola:5d} {k.get('esperando', 0):6d}  "
              f"{str(m):24.24s} {s['pedidos']:5d} {s['cobrados']:5d}")
        time.sleep(a.cada)

    print("3 · pausando la simulación (no se borra nada)")
    api.post("/api/simulacion/pause")

    # ── ¿Hay rachas? ──
    combinaciones = {json.dumps(m["marchas"], sort_keys=True) for m in muestras}
    (bien if len(combinaciones) > 1 else mal)(
        f"el reparto de marchas cambia a lo largo del rato ({len(combinaciones)} repartos distintos)")

    # ── ¿Van desacompasados? ──
    a_una = [m for m in muestras if len([v for v in m["marchas"].values() if v]) == 1 and len(m["por_bot"]) > 1]
    (bien if not a_una else mal)(
        f"nunca van todos a la misma marcha ({len(a_una)} muestras con el equipo sincronizado)")

    # ── ¿Se atasca la cocina? ──
    colas = [m["cola"] for m in muestras]
    mitad = len(colas) // 2
    crece = (sum(colas[mitad:]) / max(1, len(colas[mitad:]))) - (sum(colas[:mitad]) / max(1, mitad))
    print(f"  · cola de cocina: mínimo {min(colas)}, máximo {max(colas)}, "
          f"media {sum(colas) / len(colas):.1f}, tendencia {crece:+.1f}")
    (bien if max(colas) < 60 else mal)(f"la cola nunca llega a llenar la pantalla (máximo {max(colas)})")
    (bien if crece < 8 else mal)(f"la cola no crece sin parar (segunda mitad {crece:+.1f} de media)")

    # ── ¿Y la caja? Un pedido que se cocina pero no se cobra también es un atasco, solo que
    # se acumula en el TPV en vez de en la pantalla de cocina. ──
    abiertos = [m["abiertos"] for m in muestras]
    sube = (sum(abiertos[mitad:]) / max(1, len(abiertos[mitad:]))) - (sum(abiertos[:mitad]) / max(1, mitad))
    print(f"  · pedidos sin cobrar: mínimo {min(abiertos)}, máximo {max(abiertos)}, tendencia {sube:+.1f}")
    (bien if sube < 12 else mal)(f"la caja sigue el ritmo del servicio (sin cobrar {sube:+.1f} de media)")

    ultimo = muestras[-1]
    print(f"  · al final: {ultimo['pedidos']} pedidos de la simulación, {ultimo['cobrados']} cobrados")
    print()
    print("FALLOS: %d" % len(fallos) if fallos else "SIN FALLOS")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
