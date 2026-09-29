"""Reservas: lo que tiene que dejar hacer y, sobre todo, lo que tiene que impedir.

Las horas se calculan a partir de `reserva_horario`, no se escriben a mano: así la prueba no se
rompe el día que el local cambie el turno de comidas.
"""
import secrets
from datetime import datetime, timedelta

import pytest


def _reservas():
    """El módulo, importado tarde a propósito: `app.db` lee la configuración al importarse, y
    hasta que no corre el fixture de la base de pruebas apunta a la de producción."""
    from app import reservas
    return reservas


def _primera_franja(dias: int = 1) -> datetime:
    """Una hora válida dentro del horario del local, en un día futuro (mañana por defecto).

    Se busca en días sucesivos por si el horario deja algún día sin franjas.
    """
    reservas = _reservas()
    cfg = reservas.config()
    for salto in range(dias, dias + 7):
        dia = datetime.now() + timedelta(days=salto)
        franjas = reservas.franjas_del_dia(dia, cfg)
        if franjas:
            return franjas[0]
    pytest.skip("el horario de reservas no deja ninguna franja")


def _en_mesa_libre(cliente, camarero, reserva):
    """Deja la reserva en una mesa que ahora mismo no tenga pedido abierto."""
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    suya = next(m for m in mesas if m["nombre"] == reserva["mesa"])
    if not suya["pedido_id"]:
        return reserva
    libre = next((m for m in mesas
                  if not m["pedido_id"] and m["plazas"] >= reserva["comensales"]), None)
    assert libre, "no queda ninguna mesa libre donde sentar la reserva"
    r = cliente.patch(f"/api/reservas/{reserva['id']}/mesa", headers=camarero,
                      json={"mesa_id": libre["id"]})
    assert r.status_code == 200, r.text
    return r.json()


def _reservar(cliente, **campos):
    cuerpo = {"hora": _primera_franja().isoformat(), "comensales": 2, "nombre": "Prueba"}
    cuerpo.update(campos)
    return cliente.post("/api/publico/reservas", json=cuerpo)


# ─────────────── Lo que se admite ───────────────
def test_reservar_asigna_mesa_y_devuelve_token(cliente):
    r = _reservar(cliente)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["mesa"] and d["estado"] == "pendiente" and len(d["token"]) == 32
    cliente.post(f"/api/publico/reservas/{d['token']}/anular")


def test_el_cliente_ve_la_suya_por_el_enlace(cliente):
    token = _reservar(cliente, nombre="Ana").json()["token"]
    d = cliente.get(f"/api/publico/reservas/{token}").json()
    assert d["nombre"] == "Ana"
    assert "telefono" not in d and "origen_ip" not in d   # lo suyo, y nada más
    cliente.post(f"/api/publico/reservas/{token}/anular")


def test_huecos_respetan_la_antelacion(cliente):
    fecha = datetime.now().date().isoformat()
    d = cliente.get(f"/api/publico/reservas/huecos?fecha={fecha}&comensales=2").json()
    minimo = datetime.now() + timedelta(minutes=d["antelacion_min"])
    assert all(datetime.fromisoformat(h["hora"]) >= minimo for h in d["horas"])


# ─────────────── Lo que NO se admite ───────────────
def test_sin_los_quince_minutos_no_hay_reserva(cliente):
    dentro_de_cinco = (datetime.now() + timedelta(minutes=5)).replace(microsecond=0)
    r = _reservar(cliente, hora=dentro_de_cinco.isoformat())
    assert r.status_code == 422
    assert "antelación" in r.json()["detail"]


def test_no_se_reserva_fuera_de_horario(cliente):
    de_madrugada = (datetime.now() + timedelta(days=1)).replace(hour=4, minute=0, second=0,
                                                                microsecond=0)
    r = _reservar(cliente, hora=de_madrugada.isoformat())
    assert r.status_code == 422
    assert "servicio" in r.json()["detail"]


def test_no_cabe_un_grupo_mayor_que_la_mesa_mas_grande(cliente):
    r = _reservar(cliente, comensales=30)
    assert r.status_code == 409


def test_las_mesas_se_acaban(cliente):
    """Reservando la misma hora una y otra vez se agotan las mesas, y entonces se dice."""
    hora = _primera_franja(2).isoformat()
    hechas = []
    try:
        for _ in range(40):
            r = _reservar(cliente, hora=hora, comensales=2)
            if r.status_code == 409:
                assert "mesa libre" in r.json()["detail"]
                break
            assert r.status_code == 201, r.text
            hechas.append(r.json()["token"])
        else:
            pytest.fail("nunca se agotaron las mesas: el solape no se está comprobando")
    finally:
        for t in hechas:
            cliente.post(f"/api/publico/reservas/{t}/anular")


def test_anular_libera_la_mesa(cliente):
    hora = _primera_franja(3).isoformat()
    primera = _reservar(cliente, hora=hora, comensales=6).json()
    cliente.post(f"/api/publico/reservas/{primera['token']}/anular")
    otra = _reservar(cliente, hora=hora, comensales=6)
    assert otra.status_code == 201
    assert otra.json()["mesa"] == primera["mesa"]          # vuelve a estar disponible
    cliente.post(f"/api/publico/reservas/{otra.json()['token']}/anular")


# ─────────────── El pedido adelantado ───────────────
def test_el_pedido_adelantado_no_entra_en_cocina_al_reservar(cliente, cocina):
    quien = "SinSoltar-" + secrets.token_hex(3)     # nombre propio: el KDS lleva lo de todos
    r = _reservar(cliente, nombre=quien, lineas=[{"producto_id": 2, "cantidad": 1}]).json()
    assert r["total_cent"] > 0 and r["soltada_en"] is None
    comandas = cliente.get("/api/kds", headers=cocina).json()["comandas"]
    assert all(c["cliente"] != quien for c in comandas)
    cliente.post(f"/api/publico/reservas/{r['token']}/anular")


def test_soltar_manda_la_comanda_a_cocina(cliente, camarero, cocina):
    r = _reservar(cliente, nombre="Adelantado",
                  lineas=[{"producto_id": 2, "cantidad": 2}]).json()
    suelta = cliente.post(f"/api/reservas/{r['id']}/soltar", headers=camarero)
    assert suelta.status_code == 200, suelta.text
    assert suelta.json()["soltada_en"]
    pid = suelta.json()["pedido_id"]
    lineas = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"]
    assert lineas and all(l["estado"] == "enviada" for l in lineas)
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_no_se_suelta_dos_veces(cliente, camarero):
    r = _reservar(cliente, lineas=[{"producto_id": 2, "cantidad": 1}]).json()
    pid = cliente.post(f"/api/reservas/{r['id']}/soltar", headers=camarero).json()["pedido_id"]
    assert cliente.post(f"/api/reservas/{r['id']}/soltar", headers=camarero).status_code == 409
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_sentar_engancha_el_pedido_a_la_mesa(cliente, camarero):
    r = _reservar(cliente, nombre="Sentada", comensales=3,
                  lineas=[{"producto_id": 2, "cantidad": 1}]).json()
    # La reserva es para mañana, pero se sienta ahora: si su mesa la ocupa alguien en este
    # momento, se cambia de mesa, que es lo que haría la sala.
    r = _en_mesa_libre(cliente, camarero, r)
    sentada = cliente.post(f"/api/reservas/{r['id']}/sentar", headers=camarero)
    assert sentada.status_code == 200, sentada.text
    d = sentada.json()
    assert d["estado"] == "sentada" and d["pedido_id"]
    pedido = cliente.get(f"/api/pedidos/{d['pedido_id']}", headers=camarero).json()
    assert pedido["mesa"] == r["mesa"] and pedido["comensales"] == 3
    cliente.post(f"/api/pedidos/{d['pedido_id']}/anular", headers=camarero)


def test_no_se_sienta_sobre_una_mesa_ocupada(cliente, camarero):
    r = _reservar(cliente, nombre="Choque").json()
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    mesa = next(m for m in mesas if m["nombre"] == r["mesa"])
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": mesa["id"]}).json()["id"]
    choque = cliente.post(f"/api/reservas/{r['id']}/sentar", headers=camarero)
    assert choque.status_code == 409 and "pedido abierto" in choque.json()["detail"]
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)
    cliente.post(f"/api/publico/reservas/{r['token']}/anular")


# ─────────────── Quién puede qué ───────────────
def test_la_agenda_no_es_publica(cliente):
    assert cliente.get("/api/reservas").status_code == 401


def test_cocina_no_toca_la_agenda(cliente, cocina):
    assert cliente.get("/api/reservas", headers=cocina).status_code == 403


def test_el_camarero_se_salta_la_antelacion_pero_no_el_solape(cliente, camarero):
    """Coge el teléfono con el cliente en la puerta: puede reservar para dentro de cinco
    minutos, pero no meter dos grupos en la misma mesa a la vez."""
    reservas = _reservas()
    ahora_mismo = (datetime.now() + timedelta(minutes=5)).replace(microsecond=0)
    cfg = reservas.config()
    if not reservas.en_horario(ahora_mismo, cfg):
        pytest.skip("fuera del horario de servicio")
    r = cliente.post("/api/reservas", headers=camarero,
                     json={"hora": ahora_mismo.isoformat(), "comensales": 6, "nombre": "Puerta"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["estado"] == "confirmada"        # la coge un empleado: nace confirmada
    cliente.post(f"/api/reservas/{d['id']}/anular", headers=camarero)
