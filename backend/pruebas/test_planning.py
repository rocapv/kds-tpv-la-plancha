"""Planning de mesas: lo que necesita del servidor.

El planning es una vista (docs/PROPUESTA_PLANNING_MESAS.md) y no tiene API propia. Lo único nuevo
es que la sala, al pulsar un hueco, pide ESA mesa y no la que toque; y eso tiene que pasar las
mismas reglas que un cambio de mesa. Desde internet, en cambio, no se elige mesa.
"""
from datetime import datetime, timedelta

import pytest


def _franja(dias: int) -> datetime:
    from app import reservas
    cfg = reservas.config()
    for salto in range(dias, dias + 7):
        franjas = reservas.franjas_del_dia(datetime.now() + timedelta(days=salto), cfg)
        if franjas:
            return franjas[-1]          # la última del día: lejos de las que usan otras pruebas
    pytest.skip("el horario de reservas no deja ninguna franja")


def _mesas(cliente, camarero):
    return cliente.get("/api/mesas", headers=camarero).json()


def _anular(cliente, camarero, rid):
    cliente.post(f"/api/reservas/{rid}/anular", headers=camarero)


def test_la_sala_puede_pedir_una_mesa_concreta(cliente, camarero):
    grande = max(_mesas(cliente, camarero), key=lambda m: m["plazas"])
    r = cliente.post("/api/reservas", headers=camarero, json={
        "hora": _franja(4).isoformat(), "comensales": 2, "nombre": "Planning",
        "mesa_id": grande["id"]})
    assert r.status_code == 201, r.text
    # Sin mesa_id le habría tocado la más ajustada; con él, la que se pidió.
    assert r.json()["mesa_id"] == grande["id"]
    _anular(cliente, camarero, r.json()["id"])


def test_la_mesa_pedida_tiene_que_ser_suficiente(cliente, camarero):
    chica = min(_mesas(cliente, camarero), key=lambda m: m["plazas"])
    r = cliente.post("/api/reservas", headers=camarero, json={
        "hora": _franja(4).isoformat(), "comensales": chica["plazas"] + 1, "nombre": "Grande",
        "mesa_id": chica["id"]})
    assert r.status_code == 409
    assert "caben" in r.json()["detail"]


def test_la_mesa_pedida_no_se_pisa_con_otra_reserva(cliente, camarero):
    mesa = max(_mesas(cliente, camarero), key=lambda m: m["plazas"])
    hora = _franja(5)
    primera = cliente.post("/api/reservas", headers=camarero, json={
        "hora": hora.isoformat(), "comensales": 2, "nombre": "Primera", "mesa_id": mesa["id"]})
    assert primera.status_code == 201, primera.text
    segunda = cliente.post("/api/reservas", headers=camarero, json={
        "hora": (hora - timedelta(minutes=30)).isoformat(), "comensales": 2,
        "nombre": "Segunda", "mesa_id": mesa["id"]})
    assert segunda.status_code == 409
    assert "reservada" in segunda.json()["detail"]
    _anular(cliente, camarero, primera.json()["id"])


def test_una_mesa_que_no_existe(cliente, camarero):
    r = cliente.post("/api/reservas", headers=camarero, json={
        "hora": _franja(4).isoformat(), "comensales": 2, "nombre": "Nadie", "mesa_id": 99999})
    assert r.status_code == 404


def test_desde_internet_no_se_elige_mesa(cliente, camarero):
    mesas = _mesas(cliente, camarero)
    grande = max(mesas, key=lambda m: m["plazas"])
    r = cliente.post("/api/publico/reservas", json={
        "hora": _franja(6).isoformat(), "comensales": 2, "nombre": "Listillo",
        "mesa_id": grande["id"]})
    assert r.status_code == 201, r.text
    d = r.json()
    ajustada = min(m["plazas"] for m in mesas if m["plazas"] >= 2)
    asignada = next(m for m in mesas if m["nombre"] == d["mesa"])
    assert asignada["plazas"] == ajustada, "el mesa_id de internet se tiene que ignorar"
    cliente.post(f"/api/publico/reservas/{d['token']}/anular")


def test_las_mesas_dicen_cuantos_hay_sentados(cliente, camarero):
    m = next(m for m in _mesas(cliente, camarero) if not m["pedido_id"])
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": m["id"], "comensales": 3}).json()["id"]
    try:
        fila = next(x for x in _mesas(cliente, camarero) if x["id"] == m["id"])
        assert fila["sentados"] == 3
    finally:
        cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)
