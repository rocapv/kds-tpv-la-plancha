"""Cada uno paga lo suyo. Lo que se vigila aquí es el dinero.

La regla de oro, comprobada en varias pruebas: **lo cobrado suma exactamente la cuenta**. Ni un
céntimo de más (se cobraría dos veces algo) ni de menos (se regalaría comida).
"""
import pytest

from conftest import mesa_libre

HAMBURGUESA = 2     # 10,50
AGUA = 14           # 2,00
POSTRE = 20         # un postre cualquiera de la carta


@pytest.fixture
def mesa_con_grupo(cliente, camarero):
    """Mesa con dos comensales, un plato de cada uno y una bebida compartida."""
    mesa = mesa_libre(cliente, camarero)
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": mesa["id"]}).json()["id"]
    for producto in (HAMBURGUESA, HAMBURGUESA, AGUA):
        cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                     json={"producto_id": producto, "cantidad": 1})
    cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
    ana = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                       json={"nombre": "Ana"}).json()["id"]
    bruno = cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                         json={"nombre": "Bruno"}).json()["id"]
    lineas = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"]
    cliente.patch(f"/api/lineas/{lineas[0]['id']}/comensal", headers=camarero,
                  json={"comensal_id": ana})
    cliente.patch(f"/api/lineas/{lineas[1]['id']}/comensal", headers=camarero,
                  json={"comensal_id": bruno})
    # la tercera línea (el agua) se queda sin dueño: es de la mesa
    yield {"pedido_id": pid, "ana": ana, "bruno": bruno}
    if cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["estado"] == "abierto":
        cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def _cuenta(cliente, camarero, pid):
    return cliente.get(f"/api/pedidos/{pid}/cuenta", headers=camarero).json()


# ─────────────── El reparto ───────────────
def test_cada_uno_ve_lo_suyo_y_su_parte_de_lo_compartido(cliente, camarero, mesa_con_grupo):
    c = _cuenta(cliente, camarero, mesa_con_grupo["pedido_id"])
    assert c["compartido_pendiente_cent"] > 0
    ana = next(x for x in c["cuentas"] if x["comensal_id"] == mesa_con_grupo["ana"])
    bruno = next(x for x in c["cuentas"] if x["comensal_id"] == mesa_con_grupo["bruno"])
    assert ana["suyo_cent"] == bruno["suyo_cent"] > 0
    # el agua se parte entre los dos
    assert ana["compartido_cent"] + bruno["compartido_cent"] == c["compartido_pendiente_cent"]
    assert ana["a_pagar_cent"] + bruno["a_pagar_cent"] == c["total_cent"]


def test_cobrar_al_primero_no_cierra_la_mesa(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    r = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                     headers=camarero, json={"metodo": "tarjeta"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["concepto"] == "Ana"
    assert d["cuenta"]["pendiente_cent"] > 0
    assert cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["estado"] == "abierto"


def test_el_ultimo_paga_lo_que_falta_y_la_caja_cuadra(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    total = _cuenta(cliente, camarero, pid)["total_cent"]
    cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                 headers=camarero, json={"metodo": "tarjeta"})
    cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['bruno']}/cobrar",
                 headers=camarero, json={"metodo": "efectivo"})
    p = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()
    assert p["estado"] == "cobrado"
    assert sum(g["importe_cent"] for g in p["pagos"]) == total      # ni de más ni de menos
    assert all(l["pago_id"] for l in p["lineas"] if l["estado"] != "anulada")


def test_los_centimos_del_reparto_no_se_pierden(cliente, camarero):
    """Tres comensales y un compartido que no se divide entre tres: la suma tiene que cuadrar."""
    mesa = mesa_libre(cliente, camarero)
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": mesa["id"]}).json()["id"]
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                 json={"producto_id": AGUA, "cantidad": 1})       # 2,00 € entre tres
    cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
    ids = [cliente.post(f"/api/pedidos/{pid}/grupo", headers=camarero,
                        json={"nombre": n}).json()["id"] for n in ("A", "B", "C")]
    total = _cuenta(cliente, camarero, pid)["total_cent"]
    for cid in ids:
        cliente.post(f"/api/pedidos/{pid}/grupo/{cid}/cobrar", headers=camarero,
                     json={"metodo": "efectivo"})
    p = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()
    assert sum(g["importe_cent"] for g in p["pagos"]) == total
    assert p["estado"] == "cobrado"


def test_no_se_cobra_dos_veces_al_mismo(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                 headers=camarero, json={"metodo": "tarjeta"})
    r = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                     headers=camarero, json={"metodo": "tarjeta"})
    assert r.status_code == 409


def test_se_puede_cobrar_sin_la_parte_compartida(cliente, camarero, mesa_con_grupo):
    """El que se va antes de que llegue la botella paga solo lo suyo."""
    pid = mesa_con_grupo["pedido_id"]
    c = _cuenta(cliente, camarero, pid)
    ana = next(x for x in c["cuentas"] if x["comensal_id"] == mesa_con_grupo["ana"])
    r = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                     headers=camarero, json={"metodo": "tarjeta", "con_compartido": False})
    assert r.json()["importe_cent"] == ana["pendiente_cent"]


def test_el_efectivo_devuelve_cambio(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    r = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar", headers=camarero,
                     json={"metodo": "efectivo", "entregado_cent": 5000})
    pago = next(g for g in cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["pagos"]
                if g["id"] == r.json()["pago_id"])
    assert pago["cambio_cent"] == 5000 - r.json()["importe_cent"]


def test_no_se_paga_de_mas(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    r = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar", headers=camarero,
                     json={"metodo": "efectivo", "entregado_cent": 1})
    assert r.status_code == 422


# ─────────────── Dividir a partes iguales ───────────────
def test_dividir_entre_tres_reparte_los_centimos(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    d = cliente.get(f"/api/pedidos/{pid}/reparto?partes=3", headers=camarero).json()
    assert d["parte_cent"] * 2 + d["ultima_parte_cent"] == d["pendiente_cent"]


def test_no_se_divide_entre_uno(cliente, camarero, mesa_con_grupo):
    r = cliente.get(f"/api/pedidos/{mesa_con_grupo['pedido_id']}/reparto?partes=1",
                    headers=camarero)
    assert r.status_code == 422


# ─────────────── Tickets ───────────────
def test_el_ticket_individual_lleva_solo_lo_suyo(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    pago_id = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                           headers=camarero, json={"metodo": "tarjeta"}).json()["pago_id"]
    d = cliente.get(f"/api/pagos/{pago_id}/documento", headers=camarero).json()
    assert d["pago"]["concepto"] == "Ana"
    assert len(d["lineas"]) == 1
    assert d["base_cent"] + d["iva_cent"] == d["pago"]["importe_cent"]


def test_el_ticket_avisa_de_que_la_cuenta_va_dividida(cliente, camarero, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    primero = cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                           headers=camarero, json={"metodo": "tarjeta"}).json()["pago_id"]
    cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['bruno']}/cobrar",
                 headers=camarero, json={"metodo": "tarjeta"})
    d = cliente.get(f"/api/pagos/{primero}/documento", headers=camarero).json()
    assert d["de_varios"] and d["pagos_de_la_mesa"] == 2


# ─────────────── Quién puede ───────────────
def test_cocina_no_cobra(cliente, cocina, mesa_con_grupo):
    pid = mesa_con_grupo["pedido_id"]
    assert cliente.get(f"/api/pedidos/{pid}/cuenta", headers=cocina).status_code == 403
    assert cliente.post(f"/api/pedidos/{pid}/grupo/{mesa_con_grupo['ana']}/cobrar",
                        headers=cocina, json={"metodo": "tarjeta"}).status_code == 403
