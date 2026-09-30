"""Registro de entradas del personal (24_intentos_login.sql).

Lo que se vigila: que cada fallo quede apuntado con su IP y su vía, que el acierto también, que
lo tecleado NO se guarde nunca, y que solo lo vea gestión.
"""
PIN_MALO = "0417"


def _filas():
    from app.db import q
    return q("SELECT * FROM empleado_intentos ORDER BY id")


def test_un_pin_fallido_queda_apuntado_sin_el_pin(cliente):
    antes = len(_filas())
    r = cliente.post("/api/login", json={"pin": PIN_MALO})
    assert r.status_code == 401
    filas = _filas()
    assert len(filas) == antes + 1
    f = filas[-1]
    assert f["via"] == "pin" and not f["ok"]
    assert f["ip"] == "testclient"
    assert f["empleado_id"] is None          # con PIN no se sabe a quién se intentaba suplantar
    # Lo tecleado no está en ninguna columna.
    assert all(PIN_MALO not in str(v) for v in f.values())


def test_la_contrasena_fallida_guarda_el_numero_que_se_dijo(cliente, camarero):
    yo = cliente.get("/api/yo", headers=camarero).json()
    r = cliente.post("/api/login", json={"empleado_id": yo["id"], "contrasena": "no-es-esta-99"})
    assert r.status_code == 401
    f = _filas()[-1]
    assert f["via"] == "contrasena" and not f["ok"]
    assert f["empleado_id"] == yo["id"]
    assert all("no-es-esta-99" not in str(v) for v in f.values())


def test_la_entrada_buena_tambien_se_apunta(cliente):
    r = cliente.post("/api/login", json={"pin": "1111"})
    assert r.status_code == 200
    f = _filas()[-1]
    assert f["ok"] and f["via"] == "pin" and f["empleado_id"] == r.json()["id"]


def test_una_peticion_mal_formada_no_cuenta_como_intento(cliente):
    antes = len(_filas())
    assert cliente.post("/api/login", json={}).status_code == 422
    assert len(_filas()) == antes


def test_el_resumen_agrupa_por_ip_y_dice_quien_entro_despues(cliente, encargado):
    for _ in range(3):
        cliente.post("/api/login", json={"pin": PIN_MALO})
    cliente.post("/api/login", json={"pin": "1111"})
    r = cliente.get("/api/seguridad/intentos?horas=1", headers=encargado)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fallos"] >= 3
    fila = next(f for f in d["por_ip"] if f["ip"] == "testclient")
    assert fila["fallos"] >= 3 and fila["fallos_pin"] >= 3
    assert fila["aciertos"] >= 1
    assert fila["entraron_despues"], "tras fallar, alguien entró desde esa IP: tiene que verse"
    assert fila["origen"] == "desconocido"   # «testclient» no es una IP
    assert d["recientes"] and not d["recientes"][0]["ok"]


def test_solo_gestion_ve_el_registro(cliente, camarero, cocina):
    assert cliente.get("/api/seguridad/intentos", headers=camarero).status_code == 403
    assert cliente.get("/api/seguridad/intentos", headers=cocina).status_code == 403
    assert cliente.get("/api/seguridad/intentos").status_code == 401


def test_origen_distingue_casa_de_internet():
    from app.intentos import origen
    assert origen("192.168.1.40") == "local"
    assert origen("127.0.0.1") == "local"
    assert origen("88.18.224.11") == "internet"
    assert origen(None) == "desconocido"
