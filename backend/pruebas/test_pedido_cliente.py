"""El cliente pide desde su mesa: lo que entra solo y lo que se queda esperando.

La regla que se prueba una y otra vez aquí: **lo raro no se rechaza, se para con el motivo
escrito**. Rechazar en silencio hace que el cliente lo repita o llame al camarero, que es más
trabajo del que se ahorra.
"""
import pytest

from conftest import mesa_libre

AGUA = 14          # «Agua de deshielo», de barra
HAMBURGUESA = 2    # «Fundido de Ceres», de plancha


@pytest.fixture
def mesa(cliente, encargado, camarero):
    """Una mesa con su pantalla, su QR leído y la visita abierta: el cliente ya está sentado."""
    m = mesa_libre(cliente, camarero)
    alta = cliente.post("/api/pantallas", headers=encargado,
                        json={"mesa_id": m["id"], "nombre": "prueba"}).json()
    codigo = cliente.post("/api/pantalla/codigo",
                          headers={"X-Pantalla": alta["secreto"]}).json()["codigo"]
    v = cliente.post("/api/publico/mesa/canjear",
                     json={"codigo": codigo, "alias": "Ana"}).json()
    yield {"mesa": m, "visita": v, "cab": {"X-Visita": v["token"]}}
    # Se deja la mesa como estaba: pedido anulado, visita cerrada, pantalla de baja.
    estado = cliente.get("/api/publico/visita/comanda", headers={"X-Visita": v["token"]})
    if estado.status_code == 200:
        p = cliente.get("/api/mesas", headers=camarero).json()
        pedido = next((x["pedido_id"] for x in p if x["nombre"] == m["nombre"]), None)
        if pedido:
            cliente.post(f"/api/pedidos/{pedido}/anular", headers=camarero)
    cliente.post(f"/api/visitas/{v['id']}/cerrar", headers=camarero)
    cliente.delete(f"/api/pantallas/{alta['id']}", headers=encargado)


def _ajuste(cliente, encargado, clave, valor):
    return cliente.put(f"/api/ajustes/{clave}", headers=encargado, json={"valor": str(valor)})


# ─────────────── Lo que entra solo ───────────────
def test_un_pedido_normal_va_directo_a_cocina(cliente, cocina, mesa):
    r = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                     json={"lineas": [{"producto_id": HAMBURGUESA, "cantidad": 1},
                                      {"producto_id": AGUA, "cantidad": 2}]})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["estado"] == "en cocina" and d["pedido_id"]
    comandas = cliente.get("/api/kds", headers=cocina).json()["comandas"]
    assert any(c["pedido_id"] == d["pedido_id"] for c in comandas)


def test_el_cliente_ve_su_comanda_en_palabras_suyas(cliente, mesa):
    cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                 json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]})
    d = cliente.get("/api/publico/visita/comanda", headers=mesa["cab"]).json()
    assert d["mesa"] == mesa["mesa"]["nombre"]
    assert d["lineas"] and d["lineas"][0]["estado"] in ("en cola", "haciéndose", "listo")
    assert d["total_cent"] > 0 and d["saldo_cent"] == d["total_cent"]
    # Nada interno: ni estación de cocina ni camarero
    assert all("estacion" not in l and "camarero" not in l for l in d["lineas"])


def test_dos_tandas_van_al_mismo_pedido(cliente, mesa):
    uno = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                       json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]}).json()
    dos = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                       json={"lineas": [{"producto_id": HAMBURGUESA, "cantidad": 1}]}).json()
    assert uno["pedido_id"] == dos["pedido_id"]


# ─────────────── Lo que se queda esperando ───────────────
def test_las_mil_botellas_de_agua_se_paran(cliente, camarero, mesa):
    r = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 99}]})
    assert r.status_code == 201
    d = r.json()
    assert d["estado"] == "esperando"
    assert "99 unidades" in d["motivo"] and "10" in d["motivo"]
    # Y la sala la ve, con el motivo delante
    pendientes = cliente.get("/api/solicitudes", headers=camarero).json()
    mia = next(s for s in pendientes if s["id"] == d["solicitud_id"])
    assert "unidades" in mia["motivo_retencion"]
    cliente.post(f"/api/solicitudes/{d['solicitud_id']}/rechazar", headers=camarero,
                 json={"motivo": "prueba"})


def test_un_importe_gordo_lo_confirma_un_camarero(cliente, camarero, encargado, mesa):
    _ajuste(cliente, encargado, "cliente_max_importe_cent", 500)
    try:
        d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                         json={"lineas": [{"producto_id": HAMBURGUESA, "cantidad": 2}]}).json()
        assert d["estado"] == "esperando" and "€" in d["motivo"]
        cliente.post(f"/api/solicitudes/{d['solicitud_id']}/rechazar", headers=camarero,
                     json={"motivo": "prueba"})
    finally:
        _ajuste(cliente, encargado, "cliente_max_importe_cent", 15000)


def test_se_puede_apagar_el_pedido_directo(cliente, camarero, encargado, mesa):
    _ajuste(cliente, encargado, "cliente_pedido_directo", "no")
    try:
        d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                         json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]}).json()
        assert d["estado"] == "esperando"
        cliente.post(f"/api/solicitudes/{d['solicitud_id']}/rechazar", headers=camarero,
                     json={"motivo": "prueba"})
    finally:
        _ajuste(cliente, encargado, "cliente_pedido_directo", "si")


def test_una_categoria_puede_exigir_confirmacion(cliente, camarero, encargado, mesa):
    producto = cliente.get("/api/publico/carta").json()
    categoria = next(c["id"] for c in producto if any(p["id"] == AGUA for p in c["productos"]))
    _ajuste(cliente, encargado, "cliente_confirmar_categorias", categoria)
    try:
        d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                         json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]}).json()
        assert d["estado"] == "esperando" and "categoría" in d["motivo"]
        cliente.post(f"/api/solicitudes/{d['solicitud_id']}/rechazar", headers=camarero,
                     json={"motivo": "prueba"})
    finally:
        _ajuste(cliente, encargado, "cliente_confirmar_categorias", "")


# ─────────────── Resolver lo que espera ───────────────
def test_el_camarero_corrige_la_cantidad_y_acepta(cliente, camarero, mesa):
    d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 99}]}).json()
    pendiente = next(s for s in cliente.get("/api/solicitudes", headers=camarero).json()
                     if s["id"] == d["solicitud_id"])
    linea = pendiente["lineas"][0]
    r = cliente.post(f"/api/solicitudes/{d['solicitud_id']}/aceptar", headers=camarero,
                     json={"lineas": [{"id": linea["id"], "cantidad": 1}]})
    assert r.status_code == 200, r.text
    pedido = r.json()
    assert sum(l["cantidad"] for l in pedido["lineas"] if l["producto_id"] == AGUA) == 1


def test_rechazar_con_motivo_llega_al_telefono(cliente, camarero, mesa):
    d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 99}]}).json()
    cliente.post(f"/api/solicitudes/{d['solicitud_id']}/rechazar", headers=camarero,
                 json={"motivo": "Solo nos quedan dos botellas"})
    visto = cliente.get("/api/publico/visita/comanda", headers=mesa["cab"]).json()
    assert any(r["motivo_rechazo"] == "Solo nos quedan dos botellas" for r in visto["rechazadas"])


def test_aceptar_sin_lineas_no_se_permite(cliente, camarero, mesa):
    d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 99}]}).json()
    pendiente = next(s for s in cliente.get("/api/solicitudes", headers=camarero).json()
                     if s["id"] == d["solicitud_id"])
    r = cliente.post(f"/api/solicitudes/{d['solicitud_id']}/aceptar", headers=camarero,
                     json={"lineas": [{"id": pendiente["lineas"][0]["id"], "cantidad": 0}]})
    assert r.status_code == 409
    cliente.post(f"/api/solicitudes/{d['solicitud_id']}/rechazar", headers=camarero, json={})


# ─────────────── Lo que no se puede ───────────────
def test_sin_mesa_no_se_pide(cliente):
    r = cliente.post("/api/publico/visita/pedido",
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]})
    assert r.status_code == 401


def test_un_producto_agotado_no_cuela(cliente, encargado, mesa):
    cliente.patch(f"/api/productos/{AGUA}", headers=encargado, json={"disponible": False})
    try:
        r = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                         json={"lineas": [{"producto_id": AGUA, "cantidad": 1}]})
        assert r.status_code == 409 and "agotado" in r.json()["detail"]
    finally:
        cliente.patch(f"/api/productos/{AGUA}", headers=encargado, json={"disponible": True})


def test_el_precio_lo_pone_el_servidor(cliente, mesa):
    """El teléfono manda producto y cantidad; el precio no se negocia."""
    carta = cliente.get("/api/publico/carta").json()
    precio = next(p["precio_cent"] for c in carta for p in c["productos"] if p["id"] == AGUA)
    d = cliente.post("/api/publico/visita/pedido", headers=mesa["cab"],
                     json={"lineas": [{"producto_id": AGUA, "cantidad": 2, "precio_cent": 1}]}).json()
    assert d["total_cent"] == 2 * precio
