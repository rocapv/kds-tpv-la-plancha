"""El QR de la mesa: lo que abre una mesa y, sobre todo, lo que no la abre.

Aquí se prueba la parte que sostiene todo lo demás: si un código se pudiera reutilizar o no
caducara, cualquiera podría pedir «desde la mesa 7» sin estar sentado en ella.
"""
import pytest

from conftest import mesa_libre


@pytest.fixture
def pantalla(cliente, encargado):
    """Una pantalla dada de alta en una mesa libre. Devuelve su secreto y su mesa."""
    mesa = mesa_libre(cliente, encargado)
    r = cliente.post("/api/pantallas", headers=encargado,
                     json={"mesa_id": mesa["id"], "nombre": "de prueba"})
    assert r.status_code == 201, r.text
    d = r.json()
    yield {"mesa": mesa, "id": d["id"], "cab": {"Authorization": "Bearer " + d["secreto"]}}
    cliente.delete(f"/api/pantallas/{d['id']}", headers=encargado)


def _codigo(cliente, pantalla):
    r = cliente.post("/api/pantalla/codigo", headers=pantalla["cab"])
    assert r.status_code == 200, r.text
    return r.json()


def _cerrar(cliente, camarero, visita_id):
    cliente.post(f"/api/visitas/{visita_id}/cerrar", headers=camarero)


# ─────────────── La pantalla ───────────────
def test_la_pantalla_recibe_codigo_y_cuanto_ensenarlo(cliente, pantalla):
    d = _codigo(cliente, pantalla)
    assert d["modo"] == "rotativo"
    assert len(d["codigo"]) == 12
    assert 5 <= d["segundos"] <= 50
    assert d["codigo"] in d["url"] and d["svg"].startswith("<svg")


def test_cada_vez_un_codigo_distinto(cliente, pantalla):
    codigos = {_codigo(cliente, pantalla)["codigo"] for _ in range(5)}
    assert len(codigos) == 5


def test_sin_secreto_no_hay_codigo(cliente):
    assert cliente.post("/api/pantalla/codigo").status_code == 401
    assert cliente.post("/api/pantalla/codigo",
                        headers={"Authorization": "Bearer meloinvento"}).status_code == 401


def test_la_pantalla_dada_de_baja_deja_de_valer(cliente, encargado, pantalla):
    cliente.delete(f"/api/pantallas/{pantalla['id']}", headers=encargado)
    assert cliente.post("/api/pantalla/codigo", headers=pantalla["cab"]).status_code == 401


def test_el_secreto_solo_se_ve_al_darla_de_alta(cliente, encargado, pantalla):
    listado = cliente.get("/api/pantallas", headers=encargado).json()
    assert listado and all("secreto" not in p for p in listado)


def test_el_camarero_no_da_de_alta_pantallas(cliente, camarero):
    assert cliente.post("/api/pantallas", headers=camarero, json={"mesa_id": 1}).status_code == 403


# ─────────────── El canje ───────────────
def test_leer_el_qr_abre_la_mesa(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    r = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"], "alias": "Ana"})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["mesa"] == pantalla["mesa"]["nombre"] and len(v["token"]) == 64
    _cerrar(cliente, camarero, v["id"])


def test_un_codigo_no_se_usa_dos_veces(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    primero = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]}).json()
    segundo = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]})
    assert segundo.status_code == 409
    _cerrar(cliente, camarero, primero["id"])


def test_un_codigo_inventado_no_abre_nada(cliente):
    assert cliente.post("/api/publico/mesa/canjear",
                        json={"codigo": "ZZZZZZZZZZZZ"}).status_code == 404


def test_un_codigo_caducado_no_vale(cliente, pantalla):
    """Se envejece el código a mano en la base: esperar cincuenta segundos en una prueba, no."""
    from app.db import q
    d = _codigo(cliente, pantalla)
    q("UPDATE mesa_codigos SET caduca_en = NOW() - INTERVAL 1 SECOND WHERE codigo=%s", (d["codigo"],))
    r = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]})
    assert r.status_code == 410 and "caducado" in r.json()["detail"]


# ─────────────── La visita ───────────────
def test_con_la_mesa_abierta_la_pantalla_deja_de_rotar(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    v = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]}).json()
    siguiente = _codigo(cliente, pantalla)
    assert siguiente["modo"] == "union"
    assert siguiente["codigo"] == v["codigo_union"]
    _cerrar(cliente, camarero, v["id"])


def test_los_rezagados_se_unen_con_el_codigo_fijo(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    v = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"], "alias": "Ana"}).json()
    otro = cliente.post("/api/publico/mesa/unirse",
                        json={"codigo": v["codigo_union"], "alias": "Bruno"})
    assert otro.status_code == 200
    assert otro.json()["id"] == v["id"]                  # la misma mesa
    assert otro.json()["token"] != v["token"]            # otro teléfono
    assert otro.json()["comensales"] == 2
    _cerrar(cliente, camarero, v["id"])


def test_al_cerrar_la_mesa_mueren_los_tokens(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    v = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]}).json()
    cab = {"X-Visita": v["token"]}
    assert cliente.get("/api/publico/visita", headers=cab).status_code == 200
    _cerrar(cliente, camarero, v["id"])
    assert cliente.get("/api/publico/visita", headers=cab).status_code == 401
    # Y la pantalla vuelve a rotar
    assert _codigo(cliente, pantalla)["modo"] == "rotativo"


def test_sin_token_de_visita_no_se_ve_la_mesa(cliente):
    assert cliente.get("/api/publico/visita").status_code == 401
    assert cliente.get("/api/publico/visita", headers={"X-Visita": "meloinvento"}).status_code == 401


def test_el_token_de_la_mesa_no_abre_el_local(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    v = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]}).json()
    for ruta in ("/api/mesas", "/api/kds", "/api/informe"):
        assert cliente.get(ruta, headers={"Authorization": "Bearer " + v["token"]}).status_code == 401
    _cerrar(cliente, camarero, v["id"])


def test_el_camarero_abre_la_mesa_a_mano(cliente, camarero):
    mesa = mesa_libre(cliente, camarero)
    r = cliente.post(f"/api/mesas/{mesa['id']}/visita", headers=camarero)
    assert r.status_code == 201
    v = r.json()
    assert v["mesa"] == mesa["nombre"] and len(v["codigo_union"]) == 8
    # Y ese código sirve para que el cliente se una sin leer ningún QR
    unido = cliente.post("/api/publico/mesa/unirse", json={"codigo": v["codigo_union"]})
    assert unido.status_code == 200
    _cerrar(cliente, camarero, v["id"])


def test_la_sala_ve_las_mesas_abiertas(cliente, camarero, pantalla):
    d = _codigo(cliente, pantalla)
    v = cliente.post("/api/publico/mesa/canjear", json={"codigo": d["codigo"]}).json()
    activas = cliente.get("/api/visitas", headers=camarero).json()
    assert any(x["id"] == v["id"] and x["moviles"] == 1 for x in activas)
    _cerrar(cliente, camarero, v["id"])
