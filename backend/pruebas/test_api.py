"""Pruebas de la API: lo que tiene que funcionar y, sobre todo, lo que tiene que fallar.

Se agrupan por lo que protegen: el dinero, la cocina, la seguridad y la carta.
"""
import pytest


# ─────────────── Seguridad ───────────────
def test_sin_token_no_se_ve_nada(cliente):
    assert cliente.get("/api/mesas").status_code == 401


def test_token_inventado(cliente):
    assert cliente.get("/api/mesas", headers={"Authorization": "Bearer nome-lo-invento"}).status_code == 401


def test_pin_incorrecto(cliente):
    assert cliente.post("/api/login", json={"pin": "0000"}).status_code == 401


def test_logout_invalida_el_token(cliente):
    tok = {"Authorization": "Bearer " + cliente.post("/api/login", json={"pin": "1111"}).json()["token"]}
    assert cliente.get("/api/mesas", headers=tok).status_code == 200
    cliente.post("/api/logout", headers=tok)
    assert cliente.get("/api/mesas", headers=tok).status_code == 401


@pytest.mark.parametrize("ruta", ["/api/empleados", "/api/informe", "/api/sesiones"])
def test_camarero_no_entra_en_gestion(cliente, camarero, ruta):
    assert cliente.get(ruta, headers=camarero).status_code == 403


def test_cocina_no_abre_pedidos(cliente, cocina):
    assert cliente.post("/api/pedidos", headers=cocina,
                        json={"tipo": "sala", "mesa_id": 1}).status_code == 403


def test_camarero_no_avanza_cocina(cliente, camarero, pedido_enviado):
    assert cliente.post(f"/api/kds/pedido/{pedido_enviado}/avanzar", headers=camarero).status_code == 403


def test_el_pedido_guarda_al_camarero_de_la_sesion(cliente, camarero, encargado):
    """Aunque el cliente mienta, manda la sesión."""
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    libre = next(m for m in mesas if not m["pedido_id"])
    p = cliente.post("/api/pedidos", headers=camarero,
                     json={"tipo": "sala", "mesa_id": libre["id"], "empleado_id": 99}).json()
    assert p["camarero"] == "Laura"


# ─────────────── Dinero ───────────────
def test_no_se_cobra_sin_enviar_a_cocina(cliente, camarero):
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    libre = next(m for m in mesas if not m["pedido_id"])
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": libre["id"]}).json()["id"]
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero, json={"producto_id": 1})
    r = cliente.post(f"/api/pedidos/{pid}/cobrar", headers=camarero, json={"metodo": "tarjeta"})
    assert r.status_code == 409


def test_efectivo_insuficiente(cliente, camarero, pedido_enviado):
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero,
                     json={"metodo": "efectivo", "entregado_cent": 1})
    assert r.status_code == 422


def test_cambio_correcto(cliente, camarero, pedido_enviado):
    total = cliente.get(f"/api/pedidos/{pedido_enviado}", headers=camarero).json()["total_cent"]
    p = cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero,
                     json={"metodo": "efectivo", "entregado_cent": total + 1000}).json()
    assert p["estado"] == "cobrado"
    assert p["pagos"][0]["cambio_cent"] == 1000


def test_no_se_cobra_dos_veces(cliente, camarero, pedido_enviado):
    cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero, json={"metodo": "tarjeta"})
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero, json={"metodo": "tarjeta"})
    assert r.status_code == 409


def test_cuenta_dividida_por_lineas(cliente, camarero, pedido_enviado):
    ped = cliente.get(f"/api/pedidos/{pedido_enviado}", headers=camarero).json()
    primera = ped["lineas"][0]
    p = cliente.post(f"/api/pedidos/{pedido_enviado}/pagos", headers=camarero,
                     json={"metodo": "tarjeta", "lineas": [primera["id"]]}).json()
    assert p["estado"] == "abierto"
    assert p["pagado_cent"] == primera["cantidad"] * primera["precio_cent"]
    # esa línea ya no se puede volver a cobrar
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/pagos", headers=camarero,
                     json={"metodo": "efectivo", "lineas": [primera["id"]]})
    assert r.status_code == 409
    # y el resto liquida el pedido
    p = cliente.post(f"/api/pedidos/{pedido_enviado}/pagos", headers=camarero,
                     json={"metodo": "bizum"}).json()
    assert p["estado"] == "cobrado" and p["pendiente_cent"] == 0


def test_no_se_paga_mas_de_lo_pendiente(cliente, camarero, pedido_enviado):
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/pagos", headers=camarero,
                     json={"metodo": "tarjeta", "importe_cent": 999_999})
    assert r.status_code == 422


def test_deshacer_un_pago(cliente, camarero, pedido_enviado):
    p = cliente.post(f"/api/pedidos/{pedido_enviado}/pagos", headers=camarero,
                     json={"metodo": "efectivo", "importe_cent": 100}).json()
    pago = p["pagos"][0]["id"]
    p = cliente.request("DELETE", f"/api/pedidos/{pedido_enviado}/pagos/{pago}", headers=camarero).json()
    assert p["pagado_cent"] == 0


def test_la_suma_de_lineas_cuadra_con_el_total(cliente, camarero, pedido_enviado):
    ped = cliente.get(f"/api/pedidos/{pedido_enviado}", headers=camarero).json()
    suma = sum(l["cantidad"] * l["precio_cent"] for l in ped["lineas"] if l["estado"] != "anulada")
    assert suma == ped["total_cent"]


# ─────────────── Facturación ───────────────
def test_factura_numerada_y_unica(cliente, camarero, pedido_enviado):
    cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero, json={"metodo": "tarjeta"})
    f1 = cliente.post(f"/api/pedidos/{pedido_enviado}/factura", headers=camarero, json={}).json()
    f2 = cliente.post(f"/api/pedidos/{pedido_enviado}/factura", headers=camarero, json={}).json()
    assert f1["numero_completo"] == f2["numero_completo"]        # una factura por pedido
    assert f1["base_cent"] + f1["iva_cent"] == f1["total_cent"]  # el IVA cuadra


def test_factura_completa_exige_nif(cliente, camarero, pedido_enviado):
    cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero, json={"metodo": "tarjeta"})
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/factura", headers=camarero,
                     json={"tipo": "completa", "cliente_nombre": "Sin NIF SL"})
    assert r.status_code == 422


def test_no_se_factura_lo_no_cobrado(cliente, camarero, pedido_enviado):
    assert cliente.post(f"/api/pedidos/{pedido_enviado}/factura",
                        headers=camarero, json={}).status_code == 409


# ─────────────── Cocina ───────────────
def test_la_comanda_llega_a_su_estacion(cliente, camarero, cocina, pedido_enviado):
    plancha = cliente.get("/api/kds?estacion=plancha", headers=cocina).json()
    comanda = next(c for c in plancha["comandas"] if c["pedido_id"] == pedido_enviado)
    assert all(l["estacion"] == "plancha" for l in comanda["lineas"])
    # la bebida del pedido no está en plancha, sino en barra
    barra = cliente.get("/api/kds?estacion=barra", headers=cocina).json()
    assert any(c["pedido_id"] == pedido_enviado for c in barra["comandas"])


def test_avance_de_estados(cliente, cocina, pedido_enviado):
    estados = []
    for _ in range(3):
        estados.append(cliente.post(f"/api/kds/pedido/{pedido_enviado}/avanzar?estacion=plancha",
                                    headers=cocina).json()["estado"])
    assert estados == ["preparando", "lista", "servida"]


def test_estacion_desconocida(cliente, cocina):
    assert cliente.get("/api/kds?estacion=microondas", headers=cocina).status_code == 422


# ─────────────── Carta y usuarios ───────────────
def test_producto_agotado_no_se_puede_pedir(cliente, camarero, encargado):
    cliente.patch("/api/productos/1", headers=encargado, json={"disponible": False})
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    libre = next(m for m in mesas if not m["pedido_id"])
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": libre["id"]}).json()["id"]
    r = cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero, json={"producto_id": 1})
    assert r.status_code == 409
    cliente.patch("/api/productos/1", headers=encargado, json={"disponible": True})
    assert cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                        json={"producto_id": 1}).status_code == 200


def test_el_precio_se_congela_en_la_linea(cliente, camarero, encargado):
    """Subir el precio no debe cambiar lo que ya está pedido."""
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    libre = next(m for m in mesas if not m["pedido_id"])
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": libre["id"]}).json()["id"]
    antes = cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                         json={"producto_id": 3}).json()["total_cent"]
    cliente.patch("/api/productos/3", headers=encargado, json={"precio_cent": 9999})
    despues = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["total_cent"]
    assert antes == despues


def test_pin_repetido(cliente, encargado):
    assert cliente.post("/api/empleados", headers=encargado,
                        json={"nombre": "Copia", "rol": "cocina", "pin": "1111"}).status_code == 409


def test_pin_mal_formado(cliente, encargado):
    assert cliente.post("/api/empleados", headers=encargado,
                        json={"nombre": "Corto", "rol": "cocina", "pin": "12"}).status_code == 422


def test_siempre_queda_un_encargado(cliente, encargado):
    jefes = [e for e in cliente.get("/api/empleados", headers=encargado).json() if e["rol"] == "encargado"]
    assert len(jefes) == 1
    assert cliente.delete(f"/api/empleados/{jefes[0]['id']}", headers=encargado).status_code == 409


def test_el_empleado_de_baja_no_entra(cliente, encargado):
    nuevo = cliente.post("/api/empleados", headers=encargado,
                         json={"nombre": "Temporal", "rol": "cocina", "pin": "8765"}).json()
    assert cliente.post("/api/login", json={"pin": "8765"}).status_code == 200
    cliente.delete(f"/api/empleados/{nuevo['id']}", headers=encargado)
    assert cliente.post("/api/login", json={"pin": "8765"}).status_code == 401


# ─────────────── Informe ───────────────
def test_el_informe_cuadra_con_lo_cobrado(cliente, camarero, encargado, pedido_enviado):
    antes = cliente.get("/api/informe", headers=encargado).json()
    p = cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero,
                     json={"metodo": "tarjeta"}).json()
    despues = cliente.get("/api/informe", headers=encargado).json()
    assert despues["total_cent"] - antes["total_cent"] == p["total_cent"]
    assert despues["tickets"] == antes["tickets"] + 1
    assert despues["base_cent"] + despues["iva_cent"] == despues["total_cent"]
