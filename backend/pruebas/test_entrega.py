"""El paso que faltaba: entre «hecho» y «en la mesa» hay alguien que lo lleva.

Cocina llega hasta «lista» y ahí se para. Quien da el plato por servido es quien lo pone delante
del cliente. Sin esta separación, un plato olvidado bajo la lámpara constaba como servido y los
tiempos de sala no medían nada.
"""
import pytest


def _lineas(cliente, cab, pid):
    return cliente.get(f"/api/pedidos/{pid}", headers=cab).json()["lineas"]


def _a_lista(cliente, cocina, pid):
    """Deja toda la comanda lista en el pase, avanzándola desde cocina."""
    for _ in range(2):                       # enviada → preparando → lista
        cliente.post(f"/api/kds/pedido/{pid}/avanzar", headers=cocina)


# ─────────────── Cocina termina en «lista» ───────────────
def test_cocina_no_da_por_servido_lo_que_sigue_en_el_pase(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    assert all(l["estado"] == "lista" for l in _lineas(cliente, camarero, pedido_enviado))
    # Y el botón de avanzar ya no hace nada más: lo dice claro
    r = cliente.post(f"/api/kds/pedido/{pedido_enviado}/avanzar", headers=cocina)
    assert r.status_code == 409 and "sala" in r.json()["detail"]


def test_cocina_tampoco_marca_servida_linea_a_linea(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    lid = _lineas(cliente, camarero, pedido_enviado)[0]["id"]
    r = cliente.patch(f"/api/lineas/{lid}", headers=cocina, json={"estado": "siguiente"})
    assert r.status_code == 409 and "lleva a la mesa" in r.json()["detail"]
    directo = cliente.patch(f"/api/lineas/{lid}", headers=cocina, json={"estado": "servida"})
    assert directo.status_code == 403


def test_cocina_sigue_pudiendo_deshacer(cliente, cocina, camarero, pedido_enviado):
    """Volver atrás sí es cosa de cocina: se toca la pantalla con las manos ocupadas."""
    _a_lista(cliente, cocina, pedido_enviado)
    lid = _lineas(cliente, camarero, pedido_enviado)[0]["id"]
    r = cliente.patch(f"/api/lineas/{lid}", headers=cocina, json={"estado": "anterior"})
    assert r.status_code == 200 and r.json()["estado"] == "preparando"


# ─────────────── El pase ───────────────
def test_el_pase_ensena_lo_que_espera_a_que_lo_lleven(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    pase = cliente.get("/api/pase", headers=camarero).json()
    mia = next(c for c in pase["comandas"] if c["pedido_id"] == pedido_enviado)
    assert mia["lineas"] and all(l["esperando_seg"] >= 0 for l in mia["lineas"])


def test_el_pase_es_de_sala(cliente, cocina):
    assert cliente.get("/api/pase", headers=cocina).status_code == 403


def test_entregar_la_comanda_entera(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/entregar", headers=camarero)
    assert r.status_code == 200 and r.json()["entregadas"] >= 1
    assert all(l["estado"] == "servida" for l in _lineas(cliente, camarero, pedido_enviado))
    # Y desaparece del pase
    pase = cliente.get("/api/pase", headers=camarero).json()
    assert not any(c["pedido_id"] == pedido_enviado for c in pase["comandas"])


def test_entregar_un_plato_suelto(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    lineas = _lineas(cliente, camarero, pedido_enviado)
    r = cliente.post(f"/api/lineas/{lineas[0]['id']}/entregar", headers=camarero)
    assert r.status_code == 200
    estados = {l["id"]: l["estado"] for l in _lineas(cliente, camarero, pedido_enviado)}
    assert estados[lineas[0]["id"]] == "servida"
    assert estados[lineas[1]["id"]] == "lista"          # lo demás sigue en el pase


def test_no_se_entrega_lo_que_no_esta_hecho(cliente, camarero, pedido_enviado):
    lid = _lineas(cliente, camarero, pedido_enviado)[0]["id"]
    r = cliente.post(f"/api/lineas/{lid}/entregar", headers=camarero)
    assert r.status_code == 409 and "listo" in r.json()["detail"]


def test_entregar_dos_veces_no_cuela(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    cliente.post(f"/api/pedidos/{pedido_enviado}/entregar", headers=camarero)
    r = cliente.post(f"/api/pedidos/{pedido_enviado}/entregar", headers=camarero)
    assert r.status_code == 404


def test_cocina_no_entrega(cliente, cocina, camarero, pedido_enviado):
    _a_lista(cliente, cocina, pedido_enviado)
    assert cliente.post(f"/api/pedidos/{pedido_enviado}/entregar",
                        headers=cocina).status_code == 403
