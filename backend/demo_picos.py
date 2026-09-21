"""Genera un día de servicio con sus horas punta, para enseñar el sistema con datos creíbles.

Los pedidos se crean por la API (con su sesión, su paso por cocina y su cobro real), así que
todo lo que queda en la base de datos ha pasado por las mismas comprobaciones que en el local.
Lo único que se hace por SQL es mover las marcas de tiempo a la hora que toca: la API pone
siempre NOW(), y un día de demostración necesita comida y cena.

    python demo_picos.py                       # el día de hoy, con dos picos
    python demo_picos.py --dia 2026-09-20      # otro día
    python demo_picos.py --limpiar             # borra lo que haya creado esta herramienta

Es una herramienta de DEMOSTRACIÓN: no se usa en un local de verdad.
"""
import argparse
import json
import os
import random
import ssl
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta

SOCKET = os.getenv("KDS_DB_SOCKET", os.path.expanduser("~/.local/share/kds-mariadb/kds.sock"))
BD = os.getenv("KDS_DB_NAME", "kds_tpv")
CONTEXTO = ssl.create_default_context()
CONTEXTO.check_hostname = False
CONTEXTO.verify_mode = ssl.CERT_NONE

# Reparto de un día normal: mediodía fuerte y noche más fuerte todavía.
CURVA = {12: 4, 13: 11, 14: 14, 15: 6, 16: 2, 17: 1, 18: 1, 19: 4, 20: 10, 21: 15, 22: 8, 23: 2}
NOMBRES = ["Ana", "Joan", "Lucía", "Iker", "Marta", "Sergi", "Nerea", "Hugo", "Vera", "Nil"]


def api(base, ruta, metodo="GET", body=None, token=None):
    cab = {"Content-Type": "application/json"}
    if token:
        cab["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + "/api" + ruta, method=metodo, headers=cab,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=20, context=CONTEXTO) as r:
        return json.loads(r.read())


def sql(consulta):
    return subprocess.run(["mariadb", f"--socket={SOCKET}", "--skip-ssl", "-N", "-B", BD, "-e", consulta],
                          capture_output=True, text=True, check=True).stdout.strip()


def mover_en_el_tiempo(pedido_id, cuando):
    """Coloca el pedido entero (líneas, pagos y factura) en su hora del día."""
    abierto = cuando.strftime("%Y-%m-%d %H:%M:%S")
    enviado = (cuando + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    listo = (cuando + timedelta(minutes=random.randint(6, 18))).strftime("%Y-%m-%d %H:%M:%S")
    cerrado = (cuando + timedelta(minutes=random.randint(12, 26))).strftime("%Y-%m-%d %H:%M:%S")
    sql(f"""
      UPDATE pedidos SET abierto_en='{abierto}', cerrado_en='{cerrado}' WHERE id={pedido_id};
      UPDATE lineas_pedido SET creada_en='{abierto}', enviada_en='{enviado}',
             lista_en=IF(lista_en IS NULL, NULL, '{listo}') WHERE pedido_id={pedido_id};
      UPDATE pagos SET pagado_en='{cerrado}' WHERE pedido_id={pedido_id};
      UPDATE facturas SET emitida_en='{cerrado}' WHERE pedido_id={pedido_id};
    """)


def un_pedido(base, camareros, cocina, catalogo, cuando):
    tok = random.choice(camareros)["token"]
    mesas = api(base, "/mesas", token=tok)
    libres = [m for m in mesas if not m["pedido_id"]]
    if libres and random.random() > 0.25:
        mesa = random.choice(libres)
        p = api(base, "/pedidos", "POST", {"tipo": "sala", "mesa_id": mesa["id"]}, tok)
        comensales = random.randint(1, min(2, mesa["plazas"]))
    else:
        p = api(base, "/pedidos", "POST", {"tipo": "llevar", "cliente": random.choice(NOMBRES)}, tok)
        comensales = 1

    # Se elige por ESTACIÓN, no por el nombre de la categoría: la carta se retematiza
    # («Hamburguesas» pasó a «Placas calientes») y un nombre a fuego deja el pedido vacío.
    por_estacion = {}
    for c in catalogo:
        for x in c["productos"]:
            if x["disponible"]:
                por_estacion.setdefault(x["estacion"], []).append(x)
    if not por_estacion:
        raise RuntimeError("la carta no tiene ningún producto disponible")

    for _ in range(comensales):
        for estacion, probabilidad in (("plancha", 0.85), ("barra", 0.75), ("freidora", 0.35), ("frios", 0.15)):
            if random.random() > probabilidad or estacion not in por_estacion:
                continue
            api(base, f"/pedidos/{p['id']}/lineas", "POST",
                {"producto_id": random.choice(por_estacion[estacion])["id"]}, tok)

    if not api(base, f"/pedidos/{p['id']}", token=tok)["lineas"]:
        api(base, f"/pedidos/{p['id']}/lineas", "POST",
            {"producto_id": random.choice(next(iter(por_estacion.values())))["id"]}, tok)

    api(base, f"/pedidos/{p['id']}/enviar", "POST", token=tok)
    for _ in range(3):                                    # cocina: empezar, listo, servido
        api(base, f"/kds/pedido/{p['id']}/avanzar", "POST", token=cocina["token"])

    total = api(base, f"/pedidos/{p['id']}", token=tok)["total_cent"]
    metodo = random.choices(["tarjeta", "efectivo", "bizum"], weights=[6, 3, 1])[0]
    cuerpo = {"metodo": metodo}
    if metodo == "efectivo":
        cuerpo["entregado_cent"] = -(-total // 500) * 500
    api(base, f"/pedidos/{p['id']}/cobrar", "POST", cuerpo, tok)
    if random.random() < 0.25:                            # una cuarta parte pide factura
        api(base, f"/pedidos/{p['id']}/factura", "POST", {}, tok)

    mover_en_el_tiempo(p["id"], cuando)
    return p["id"], total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://192.168.1.105:8443")
    ap.add_argument("--dia", default=date.today().isoformat())
    ap.add_argument("--limpiar", action="store_true")
    a = ap.parse_args()

    if a.limpiar:
        n = sql(f"SELECT COUNT(*) FROM pedidos WHERE DATE(abierto_en)='{a.dia}'")
        sql(f"""DELETE f FROM facturas f JOIN pedidos p ON p.id=f.pedido_id WHERE DATE(p.abierto_en)='{a.dia}';
                DELETE g FROM pagos g JOIN pedidos p ON p.id=g.pedido_id WHERE DATE(p.abierto_en)='{a.dia}';
                DELETE l FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id WHERE DATE(p.abierto_en)='{a.dia}';
                DELETE FROM pedidos WHERE DATE(abierto_en)='{a.dia}';""")
        # El arqueo de ese día se calculó con las ventas que se acaban de borrar: se retira
        # para que no quede un cierre Z hablando de dinero que ya no existe.
        sql(f"DELETE FROM arqueos WHERE fecha='{a.dia}'")
        print(f"borrados {n} pedidos del {a.dia}")
        return 0

    camareros = [api(a.url, "/login", "POST", {"pin": p}) for p in ("1111", "2222")]
    cocina = api(a.url, "/login", "POST", {"pin": "3333"})
    catalogo = api(a.url, "/catalogo", token=camareros[0]["token"])

    total_dia, hechos = 0, 0
    for hora, cuantos in sorted(CURVA.items()):
        for _ in range(cuantos):
            cuando = datetime.fromisoformat(a.dia).replace(
                hour=hora, minute=random.randint(0, 32), second=random.randint(0, 59))
            try:
                pid, total = un_pedido(a.url, camareros, cocina, catalogo, cuando)
            except Exception as e:                        # una mesa ocupada no debe parar el día
                print(f"  · {hora:02d}h: {e}", file=sys.stderr)
                continue
            total_dia += total
            hechos += 1
        print(f"{hora:02d}h · {cuantos:2d} pedidos" + " ▇" * cuantos)

    print(f"\n{hechos} pedidos · {total_dia/100:.2f} € el {a.dia}")
    print("Reparto por horas en el informe del día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
