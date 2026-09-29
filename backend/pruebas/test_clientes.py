"""Cuentas de cliente: entrar, quedarse dentro y, sobre todo, no poder entrar en el local.

La cuenta del cliente se crea desde internet, así que lo que más se comprueba aquí es lo que NO
puede hacer su token.
"""
import secrets

import pytest


def _correo():
    return f"prueba-{secrets.token_hex(4)}@ejemplo.test"


@pytest.fixture
def cuenta(cliente):
    email = _correo()
    r = cliente.post("/api/publico/clientes/registro",
                     json={"email": email, "contrasena": "unaclavelarga", "nombre": "Ana"})
    assert r.status_code == 201, r.text
    d = r.json()
    return {"email": email, "clave": "unaclavelarga", "token": d["token"], "id": d["id"],
            "cab": {"Authorization": "Bearer " + d["token"]}}


# ─────────────── Alta y entrada ───────────────
def test_el_alta_devuelve_token_y_perfil(cuenta):
    assert len(cuenta["token"]) == 64 and cuenta["id"]


def test_no_se_repite_el_correo(cliente, cuenta):
    r = cliente.post("/api/publico/clientes/registro",
                     json={"email": cuenta["email"], "contrasena": "otraclavelarga"})
    assert r.status_code == 409


def test_contrasena_corta_no_vale(cliente):
    r = cliente.post("/api/publico/clientes/registro",
                     json={"email": _correo(), "contrasena": "corta"})
    assert r.status_code == 422


def test_correo_mal_escrito_no_vale(cliente):
    r = cliente.post("/api/publico/clientes/registro",
                     json={"email": "esto-no-es-un-correo", "contrasena": "unaclavelarga"})
    assert r.status_code == 422


def test_entrar_y_seguir_dentro(cliente, cuenta):
    r = cliente.post("/api/publico/clientes/entrar",
                     json={"email": cuenta["email"], "contrasena": cuenta["clave"]})
    assert r.status_code == 200
    otro = {"Authorization": "Bearer " + r.json()["token"]}
    # Las dos sesiones valen a la vez: el móvil y la tableta de casa.
    assert cliente.get("/api/publico/clientes/yo", headers=otro).status_code == 200
    assert cliente.get("/api/publico/clientes/yo", headers=cuenta["cab"]).status_code == 200


def test_contrasena_equivocada(cliente, cuenta):
    r = cliente.post("/api/publico/clientes/entrar",
                     json={"email": cuenta["email"], "contrasena": "noeslasuya"})
    assert r.status_code == 401
    # El mensaje no dice si el fallo fue el correo o la contraseña.
    assert "no existe" not in r.json()["detail"].lower()


def test_salir_invalida_el_token(cliente, cuenta):
    assert cliente.post("/api/publico/clientes/salir", headers=cuenta["cab"]).status_code == 200
    assert cliente.get("/api/publico/clientes/yo", headers=cuenta["cab"]).status_code == 401


def test_la_contrasena_nunca_sale(cliente, cuenta):
    d = cliente.get("/api/publico/clientes/yo", headers=cuenta["cab"]).json()
    assert "contrasena" not in d and "token" not in d
    assert d["email"] == cuenta["email"]


# ─────────────── Perfil y factura automática ───────────────
def test_guardar_datos_fiscales(cliente, cuenta):
    r = cliente.patch("/api/publico/clientes/yo", headers=cuenta["cab"],
                      json={"nif": "12345678Z", "razon_social": "Ana SL", "factura_auto": True})
    assert r.status_code == 200
    d = r.json()
    assert d["nif"] == "12345678Z" and d["factura_auto"] is True


def test_cambiar_contrasena_echa_a_los_demas_aparatos(cliente, cuenta):
    otro = cliente.post("/api/publico/clientes/entrar",
                        json={"email": cuenta["email"], "contrasena": cuenta["clave"]}).json()
    otra_cab = {"Authorization": "Bearer " + otro["token"]}
    r = cliente.post("/api/publico/clientes/contrasena", headers=cuenta["cab"],
                     json={"actual": cuenta["clave"], "nueva": "otraclavemuylarga"})
    assert r.status_code == 200
    assert cliente.get("/api/publico/clientes/yo", headers=otra_cab).status_code == 401   # fuera
    assert cliente.get("/api/publico/clientes/yo", headers=cuenta["cab"]).status_code == 200  # este no


def test_no_se_cambia_sin_saber_la_de_ahora(cliente, cuenta):
    r = cliente.post("/api/publico/clientes/contrasena", headers=cuenta["cab"],
                     json={"actual": "meloinvento", "nueva": "otraclavemuylarga"})
    assert r.status_code == 401


# ─────────────── Lo que un cliente NO puede ───────────────
@pytest.mark.parametrize("ruta", ["/api/mesas", "/api/kds", "/api/informe", "/api/empleados",
                                  "/api/reservas", "/api/almacen", "/api/ajustes"])
def test_el_token_de_cliente_no_abre_el_local(cliente, cuenta, ruta):
    assert cliente.get(ruta, headers=cuenta["cab"]).status_code in (401, 403)


def test_el_token_de_empleado_no_vale_como_cliente(cliente, camarero):
    assert cliente.get("/api/publico/clientes/yo", headers=camarero).status_code == 401


def test_sin_token_no_hay_perfil(cliente):
    assert cliente.get("/api/publico/clientes/yo").status_code == 401
