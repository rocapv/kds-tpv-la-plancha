"""El grupo de la mesa: quién ocupa cada sitio y de quién es cada plato.

Lo que se protege aquí: que repartir sea opcional (una mesa sin comensales funciona igual que
siempre), que lo que pide un móvil quede a su nombre solo, y que nada de esto toque una línea que
ya está pagada.
"""
import pytest

from conftest import mesa_libre

AGUA = 14
HAMBURGUESA = 2


@pytest.fixture
def pedido_en_mesa(cliente, camarero):
    mesa = mesa_libre(cliente, camarero)
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": mesa["id"]}).json()["id"]
    for producto in (HAMBURGUESA, AGUA):
        cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                     json={"producto_id": producto, "cantidad": 1})
    yield {"pedido_id": pid, "mesa": mesa}
    if cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["estado"] == "abierto":
        cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


# ─────────────── La rejilla ───────────────
def test_la_rejilla_tiene_el_tamano_de_la_mesa(cliente, camarero, pedido_en_mesa):
    d = cliente.get(f"/api/pedidos/{pedido_en_mesa['pedido_id']}/grupo",
                    headers=camarero).json()
    assert d["plazas"] == pedido_en_mesa["mesa"]["plazas"]
    assert len(d["rejilla"]) == d["plazas"]
    assert all(s.get("libre") for s in d["rejilla"])        # nadie sentado todavía


def test_lo_no_repartido_es_de_la_mesa(cliente, camarero, pedido_en_mesa):
    d = cliente.get(f"/api/pedidos/{pedido_en_mesa['pedido_id']}/grupo",
                    headers=camarero).json()
    assert len(d["de_la_mesa"]["lineas"]) == 2
    assert d["de_la_mesa"]["total_cent"] == d["total_cent"]


def test_sentar_a_alguien_y_ponerle_nombre(cliente, camarero, pedido_en_mesa):
    pid = pedido_en_mesa["pedido_id"]
    c = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                     json={"sitio": 1, "nombre": "Ana"}).json()
    assert c["sitio"] == 1 and c["nombre"] == "Ana"
    otro = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                        json={"nombre": "Bruno"}).json()
    assert otro["sitio"] == 2                                # el primero libre
    d = cliente.get(f"/api/pedidos/{pid}/grupo", headers=camarero).json()
    assert [s["nombre"] for s in d["rejilla"][:2]] == ["Ana", "Bruno"]


def test_no_se_sientan_dos_en_el_mismo_sitio(cliente, camarero, pedido_en_mesa):
    pid = pedido_en_mesa["pedido_id"]
    cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero, json={"sitio": 3})
    r = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero, json={"sitio": 3})
    assert r.status_code == 409


def test_renombrar_a_quien_esta_sentado(cliente, camarero, pedido_en_mesa):
    pid = pedido_en_mesa["pedido_id"]
    cid = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                       json={"nombre": "el de la gorra"}).json()["id"]
    r = cliente.patch(f"/api/grupo/{cid}", headers=camarero, json={"nombre": "Carmen"})
    assert r.status_code == 200 and r.json()["nombre"] == "Carmen"


# ─────────────── Repartir los platos ───────────────
def test_eso_es_mio(cliente, camarero, pedido_en_mesa):
    pid = pedido_en_mesa["pedido_id"]
    cid = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                       json={"nombre": "Ana"}).json()["id"]
    linea = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"][0]
    r = cliente.patch(f"/api/lineas/{linea['id']}/comensal", headers=camarero,
                      json={"comensal_id": cid})
    assert r.status_code == 200
    d = cliente.get(f"/api/pedidos/{pid}/grupo", headers=camarero).json()
    suyo = next(s for s in d["rejilla"] if s["id"] == cid)
    assert len(suyo["lineas"]) == 1 and suyo["total_cent"] > 0
    assert len(d["de_la_mesa"]["lineas"]) == 1              # la otra sigue siendo compartida


def test_devolver_un_plato_a_la_mesa(cliente, camarero, pedido_en_mesa):
    pid = pedido_en_mesa["pedido_id"]
    cid = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero, json={}).json()["id"]
    linea = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"][0]
    cliente.patch(f"/api/lineas/{linea['id']}/comensal", headers=camarero,
                  json={"comensal_id": cid})
    cliente.patch(f"/api/lineas/{linea['id']}/comensal", headers=camarero,
                  json={"comensal_id": None})
    d = cliente.get(f"/api/pedidos/{pid}/grupo", headers=camarero).json()
    assert len(d["de_la_mesa"]["lineas"]) == 2


def test_un_plato_de_otra_mesa_no_se_cuela(cliente, camarero, pedido_en_mesa):
    pid = pedido_en_mesa["pedido_id"]
    linea = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"][0]
    r = cliente.patch(f"/api/lineas/{linea['id']}/comensal", headers=camarero,
                      json={"comensal_id": 999999})
    assert r.status_code == 404


def test_al_levantarse_lo_suyo_pasa_a_la_mesa(cliente, camarero, pedido_en_mesa):
    """Se va, pero lo que pidió alguien se lo ha comido: sigue habiendo que cobrarlo."""
    pid = pedido_en_mesa["pedido_id"]
    cid = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                       json={"nombre": "Dani"}).json()["id"]
    linea = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"][0]
    cliente.patch(f"/api/lineas/{linea['id']}/comensal", headers=camarero,
                  json={"comensal_id": cid})
    cliente.delete(f"/api/grupo/{cid}", headers=camarero)
    d = cliente.get(f"/api/pedidos/{pid}/grupo", headers=camarero).json()
    assert len(d["de_la_mesa"]["lineas"]) == 2
    assert d["total_cent"] > 0                              # no se ha perdido nada


# ─────────────── Desde el móvil ───────────────
def test_lo_que_pide_un_movil_queda_a_su_nombre(cliente, encargado, camarero):
    m = mesa_libre(cliente, camarero)
    alta = cliente.post("/api/pantallas", headers=encargado,
                        json={"mesa_id": m["id"]}).json()
    codigo = cliente.post("/api/pantalla/codigo",
                          headers={"X-Pantalla": alta["secreto"]}).json()["codigo"]
    v = cliente.post("/api/publico/mesa/canjear",
                     json={"codigo": codigo, "alias": "Ana"}).json()
    r = cliente.post("/api/publico/visita/pedido", headers={"X-Visita": v["token"]},
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]}).json()
    d = cliente.get(f"/api/pedidos/{r['pedido_id']}/grupo", headers=camarero).json()
    suyo = next((s for s in d["rejilla"] if s["nombre"] == "Ana"), None)
    assert suyo and len(suyo["lineas"]) == 1 and suyo["con_movil"]
    assert not d["de_la_mesa"]["lineas"]                    # nada quedó sin dueño

    cliente.post(f"/api/pedidos/{r['pedido_id']}/anular", headers=camarero)
    cliente.post(f"/api/visitas/{v['id']}/cerrar", headers=camarero)
    cliente.delete(f"/api/pantallas/{alta['id']}", headers=encargado)


# ─────────────── Quién puede ───────────────
def test_cocina_no_reparte_la_cuenta(cliente, cocina, pedido_en_mesa):
    assert cliente.get(f"/api/pedidos/{pedido_en_mesa['pedido_id']}/grupo",
                       headers=cocina).status_code == 403
