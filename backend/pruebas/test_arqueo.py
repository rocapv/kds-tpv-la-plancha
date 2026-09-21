"""Pruebas del arqueo de caja y el cierre Z.

Van en un fichero aparte porque son un flujo con orden: la caja se abre una vez, se mueve
dinero y se cierra una vez, y cada prueba comprueba un eslabón de esa cadena. Los importes se
comprueban por diferencia (antes / después), no por su valor absoluto, para que no dependan de
lo que hayan vendido las demás pruebas.
"""
FONDO = 15000


def caja(cliente, encargado):
    return cliente.get("/api/arqueo", headers=encargado).json()


def pedido_en_efectivo(cliente, camarero, producto=1):
    """Un pedido cobrado en efectivo: lo que de verdad llena el cajón.

    Va «para llevar» para no depender de que queden mesas libres a estas alturas de la sesión.
    """
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "llevar", "cliente": "Prueba"}).json()["id"]
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero, json={"producto_id": producto})
    cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
    total = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["total_cent"]
    r = cliente.post(f"/api/pedidos/{pid}/cobrar", headers=camarero,
                     json={"metodo": "efectivo", "entregado_cent": total})
    assert r.status_code == 200, r.text
    return total


# ─────────────── Apertura ───────────────
def test_el_camarero_no_abre_la_caja(cliente, camarero):
    assert cliente.post("/api/arqueo/apertura", headers=camarero,
                        json={"fondo_cent": FONDO}).status_code == 403


def test_apertura_declara_el_fondo(cliente, encargado):
    r = cliente.post("/api/arqueo/apertura", headers=encargado, json={"fondo_cent": FONDO})
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["arqueo"]["estado"] == "abierto"
    assert e["fondo_cent"] == FONDO
    assert e["esperado_cent"] == FONDO + e["ventas_efectivo_cent"]


def test_la_caja_no_se_abre_dos_veces(cliente, encargado):
    assert cliente.post("/api/arqueo/apertura", headers=encargado,
                        json={"fondo_cent": 100}).status_code == 409


# ─────────────── Durante el servicio ───────────────
def test_el_efectivo_cobrado_sube_lo_esperado(cliente, camarero, encargado):
    antes = caja(cliente, encargado)
    total = pedido_en_efectivo(cliente, camarero)
    ahora = caja(cliente, encargado)
    assert ahora["ventas_efectivo_cent"] == antes["ventas_efectivo_cent"] + total
    assert ahora["esperado_cent"] == antes["esperado_cent"] + total


def test_la_tarjeta_no_sube_lo_esperado(cliente, camarero, encargado, pedido_enviado):
    antes = caja(cliente, encargado)
    cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero, json={"metodo": "tarjeta"})
    ahora = caja(cliente, encargado)
    assert ahora["esperado_cent"] == antes["esperado_cent"]
    assert ahora["ventas_total_cent"] > antes["ventas_total_cent"]


def test_salida_y_entrada_de_efectivo(cliente, camarero, encargado):
    antes = caja(cliente, encargado)
    r = cliente.post("/api/arqueo/movimientos", headers=camarero,
                     json={"tipo": "salida", "importe_cent": 2500, "motivo": "Pan del día"})
    assert r.status_code == 201, r.text
    assert r.json()["esperado_cent"] == antes["esperado_cent"] - 2500
    r = cliente.post("/api/arqueo/movimientos", headers=encargado,
                     json={"tipo": "entrada", "importe_cent": 1000, "motivo": "Reponer cambio"})
    assert r.json()["esperado_cent"] == antes["esperado_cent"] - 1500


def test_movimiento_con_tipo_inventado(cliente, encargado):
    assert cliente.post("/api/arqueo/movimientos", headers=encargado,
                        json={"tipo": "regalo", "importe_cent": 100, "motivo": "x"}).status_code == 422


def test_movimiento_con_importe_negativo(cliente, encargado):
    assert cliente.post("/api/arqueo/movimientos", headers=encargado,
                        json={"tipo": "entrada", "importe_cent": -100, "motivo": "x"}).status_code == 422


def test_quitar_un_movimiento_lo_descuenta(cliente, encargado):
    r = cliente.post("/api/arqueo/movimientos", headers=encargado,
                     json={"tipo": "salida", "importe_cent": 700, "motivo": "Error de tecleo"})
    antes = r.json()
    mid = antes["movimientos"][-1]["id"]
    ahora = cliente.delete(f"/api/arqueo/movimientos/{mid}", headers=encargado).json()
    assert ahora["esperado_cent"] == antes["esperado_cent"] + 700


# ─────────────── Cierre ───────────────
def test_el_camarero_no_cierra_la_caja(cliente, camarero, encargado):
    e = caja(cliente, encargado)
    assert cliente.post("/api/arqueo/cierre", headers=camarero,
                        json={"contado_cent": e["esperado_cent"]}).status_code == 403


def test_no_se_cierra_con_pedidos_sin_cobrar(cliente, camarero, encargado, pedido_enviado):
    e = caja(cliente, encargado)
    r = cliente.post("/api/arqueo/cierre", headers=encargado, json={"contado_cent": e["esperado_cent"]})
    assert r.status_code == 409
    assert f"#{pedido_enviado}" in r.json()["detail"]


def test_el_recuento_tiene_que_cuadrar(cliente, encargado):
    e = caja(cliente, encargado)
    r = cliente.post("/api/arqueo/cierre?forzar=true", headers=encargado,
                     json={"contado_cent": e["esperado_cent"], "recuento": {"5000": 1}})
    assert r.status_code == 422
    assert "recuento" in r.json()["detail"]


def test_no_se_retira_mas_de_lo_contado(cliente, encargado):
    assert cliente.post("/api/arqueo/cierre?forzar=true", headers=encargado,
                        json={"contado_cent": 1000, "retirada_cent": 5000}).status_code == 422


def test_cierre_z_firmado_y_con_descuadre(cliente, encargado):
    e = caja(cliente, encargado)
    esperado = e["esperado_cent"]
    contado = esperado - 500                       # faltan 5 €: descuadre a propósito
    r = cliente.post("/api/arqueo/cierre?forzar=true", headers=encargado,
                     json={"contado_cent": contado, "retirada_cent": 1000,
                           "recuento": {"1": contado}, "notas": "Cambio mal dado"})
    assert r.status_code == 200, r.text
    a = r.json()["arqueo"]
    assert a["estado"] == "cerrado"
    assert a["numero_z"].startswith("Z") and a["numero_z"].endswith("/00001")
    assert a["esperado_cent"] == esperado
    assert a["diferencia_cent"] == -500
    assert a["retirada_cent"] == 1000
    assert a["fondo_siguiente_cent"] == contado - 1000
    assert a["cerrado_por_nombre"] == "Pau"
    assert a["fondo_cent"] == FONDO


def test_la_caja_cerrada_no_se_cierra_otra_vez(cliente, encargado):
    assert cliente.post("/api/arqueo/cierre?forzar=true", headers=encargado,
                        json={"contado_cent": 100}).status_code == 409


def test_la_caja_cerrada_no_admite_movimientos(cliente, encargado):
    assert cliente.post("/api/arqueo/movimientos", headers=encargado,
                        json={"tipo": "entrada", "importe_cent": 100, "motivo": "tarde"}).status_code == 409


def test_el_cierre_congela_las_cifras(cliente, camarero, encargado):
    """Cobrar después del cierre no puede cambiar lo que dice el Z."""
    antes = caja(cliente, encargado)["arqueo"]
    pedido_en_efectivo(cliente, camarero)
    despues = caja(cliente, encargado)["arqueo"]
    assert despues["esperado_cent"] == antes["esperado_cent"]
    assert despues["ventas_efectivo_cent"] == antes["ventas_efectivo_cent"]


def test_el_cierre_sale_en_el_historico(cliente, encargado):
    z = caja(cliente, encargado)["arqueo"]["numero_z"]
    historico = cliente.get("/api/arqueos", headers=encargado).json()
    assert any(f["numero_z"] == z and f["diferencia_cent"] == -500 for f in historico)


def test_el_camarero_no_ve_el_historico(cliente, camarero):
    assert cliente.get("/api/arqueos", headers=camarero).status_code == 403
