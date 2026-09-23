"""El tope de las pantallas que se pintan solas: que una cocina atascada no tumbe la tableta."""
from conftest import mesa_libre


def test_kds_devuelve_cuantas_esperan(cliente, camarero, cocina):
    """Con más comandas que el tope, se mandan las más viejas y se dice cuántas quedan."""
    abiertos = []
    for i in range(4):
        pid = cliente.post("/api/pedidos", headers=camarero,
                           json={"tipo": "llevar", "cliente": f"Tope {i}"}).json()["id"]
        cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                     json={"producto_id": 2, "cantidad": 1})
        cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
        abiertos.append(pid)

    d = cliente.get("/api/kds?limite=2", headers=cocina).json()
    assert len(d["comandas"]) == 2, "el tope no se respeta"
    assert d["esperando"] >= 2, f"no dice cuántas esperan: {d['esperando']}"
    # y son las MÁS VIEJAS: en cocina se despacha por orden de llegada
    assert [c["pedido_id"] for c in d["comandas"]] == sorted(c["pedido_id"] for c in d["comandas"])
    primeras = [c["pedido_id"] for c in d["comandas"]]
    assert abiertos[-1] not in primeras, "la última comanda no puede adelantar a las que esperaban"

    entero = cliente.get("/api/kds", headers=cocina).json()
    assert entero["esperando"] == 0 or len(entero["comandas"]) == 60
    for pid in abiertos:
        cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_limite_absurdo_no_tumba_la_consulta(cliente, cocina):
    for limite in (0, -5, 99999):
        r = cliente.get(f"/api/kds?limite={limite}", headers=cocina)
        assert r.status_code == 200
        assert len(r.json()["comandas"]) <= 500


def test_recogida_tambien_tiene_tope(cliente):
    d = cliente.get("/api/recogida").json()
    assert "mas_listos" in d and "mas_preparando" in d
    assert len(d["listos"]) <= 24 and len(d["preparando"]) <= 24
