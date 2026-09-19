"""Simulador de servicio para la demo: camareros que piden, cocina que prepara, caja que cobra.

Usa SOLO la API pública (igual que las pantallas), así la demo también prueba el backend.
    python simulador.py                  # servicio continuo contra http://localhost:8090
    python simulador.py --pedidos 20 --rapido
    python simulador.py --sin-cocina     # deja que la cocina la lleve una persona en el KDS
"""
import argparse
import json
import random
import time
import urllib.request

NOTAS = [None, None, None, "Sin cebolla", "Muy hecha", "Sin pepinillo", "Sin gluten", "Extra de queso"]
NOMBRES = ["Ana", "Joan", "Lucía", "Iker", "Marta", "Sergi", "Nerea", "Hugo"]


def api(base, ruta, metodo="GET", body=None):
    req = urllib.request.Request(base + "/api" + ruta, method=metodo,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8090")
    ap.add_argument("--pedidos", type=int, default=0, help="0 = sin fin")
    ap.add_argument("--rapido", action="store_true", help="tiempos x10 más cortos")
    ap.add_argument("--sin-cocina", action="store_true")
    a = ap.parse_args()
    k = 0.1 if a.rapido else 1.0

    cat = api(a.url, "/catalogo")
    por_cat = {c["nombre"]: c["productos"] for c in cat}
    camareros = [api(a.url, "/login", "POST", {"pin": p})["id"] for p in ("1111", "2222")]
    hechos = 0
    en_curso = []  # (pedido_id, momento_cobro)

    while not a.pedidos or hechos < a.pedidos or en_curso:
        # 1) nuevo cliente
        if (not a.pedidos or hechos < a.pedidos) and random.random() < 0.5:
            libres = [m for m in api(a.url, "/mesas") if not m["pedido_id"]]
            if random.random() < 0.25 or not libres:
                p = api(a.url, "/pedidos", "POST", {"empleado_id": random.choice(camareros),
                                                     "tipo": "llevar", "cliente": random.choice(NOMBRES)})
                comensales = 1
            else:
                m = random.choice(libres)
                p = api(a.url, "/pedidos", "POST", {"empleado_id": random.choice(camareros),
                                                     "tipo": "sala", "mesa_id": m["id"]})
                comensales = random.randint(1, m["plazas"])
            for _ in range(comensales):
                api(a.url, f"/pedidos/{p['id']}/lineas", "POST",
                    {"producto_id": random.choice(por_cat["Hamburguesas"])["id"], "notas": random.choice(NOTAS)})
                api(a.url, f"/pedidos/{p['id']}/lineas", "POST", {"producto_id": random.choice(por_cat["Bebidas"])["id"]})
                if random.random() < 0.7:
                    api(a.url, f"/pedidos/{p['id']}/lineas", "POST", {"producto_id": random.choice(por_cat["Entrantes"])["id"]})
            api(a.url, f"/pedidos/{p['id']}/enviar", "POST")
            en_curso.append((p["id"], time.time() + random.uniform(120, 300) * k))
            hechos += 1
            print(f"+ pedido #{p['id']} ({p['tipo']}, {comensales} pax)")

        # 2) cocina: avanza una comanda al azar
        if not a.sin_cocina:
            comandas = api(a.url, "/kds")["comandas"]
            if comandas:
                c = random.choice(comandas[:4])  # suele atender las más antiguas
                api(a.url, f"/kds/pedido/{c['pedido_id']}/avanzar", "POST")

        # 3) caja: cobra lo que ya se ha servido y ha pasado su tiempo
        for pid, cuando in list(en_curso):
            if time.time() < cuando:
                continue
            ped = api(a.url, f"/pedidos/{pid}")
            if ped["estado"] != "abierto":
                en_curso.remove((pid, cuando)); continue
            if any(l["estado"] in ("enviada", "preparando") for l in ped["lineas"]):
                continue
            metodo = random.choice(["tarjeta", "tarjeta", "efectivo", "bizum"])
            body = {"metodo": metodo}
            if metodo == "efectivo":
                body["entregado_cent"] = -(-ped["total_cent"] // 500) * 500
            api(a.url, f"/pedidos/{pid}/cobrar", "POST", body)
            en_curso.remove((pid, cuando))
            print(f"€ cobrado #{pid} {ped['total_cent']/100:.2f} € ({metodo})")

        time.sleep(random.uniform(5, 15) * k)


if __name__ == "__main__":
    main()
