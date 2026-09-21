"""Pruebas del modo sin red: que lo apuntado en la tableta se envíe UNA vez.

El peligro del modo sin red no es perder una comanda, es duplicarla: basta con que la petición
llegara al servidor y se perdiera la respuesta para que el reenvío cree un pedido gemelo. Aquí
se comprueba la pieza del servidor que lo impide (la clave de idempotencia) reproduciendo lo
que hace el TPV al reconectar: reenviar exactamente lo mismo con la misma clave.
"""
import uuid

from conftest import mesa_libre


def clave():
    return str(uuid.uuid4())


def cab(token, k):
    return {**token, "Idempotency-Key": k}


# ─────────────── Una acción, una vez ───────────────
def test_reenviar_un_pedido_no_crea_dos(cliente, camarero):
    k = clave()
    cuerpo = {"tipo": "llevar", "cliente": "Sin red"}
    antes = len(cliente.get("/api/pedidos", headers=camarero).json())

    uno = cliente.post("/api/pedidos", headers=cab(camarero, k), json=cuerpo)
    dos = cliente.post("/api/pedidos", headers=cab(camarero, k), json=cuerpo)

    assert uno.status_code == dos.status_code == 200
    assert uno.json()["id"] == dos.json()["id"]
    assert dos.headers.get("X-Idempotencia") == "repetida"
    assert len(cliente.get("/api/pedidos", headers=camarero).json()) == antes + 1

    cliente.post(f"/api/pedidos/{uno.json()['id']}/anular", headers=camarero)


def test_sin_clave_se_duplica(cliente, camarero):
    """La protección es de la clave, no del contenido: sin clave, dos peticiones son dos."""
    cuerpo = {"tipo": "llevar", "cliente": "Repetido"}
    uno = cliente.post("/api/pedidos", headers=camarero, json=cuerpo).json()
    dos = cliente.post("/api/pedidos", headers=camarero, json=cuerpo).json()
    assert uno["id"] != dos["id"]
    for p in (uno, dos):
        cliente.post(f"/api/pedidos/{p['id']}/anular", headers=camarero)


def test_reenviar_una_linea_no_la_duplica(cliente, camarero):
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "llevar", "cliente": "Línea"}).json()["id"]
    k = clave()
    cuerpo = {"producto_id": 2, "cantidad": 1}
    uno = cliente.post(f"/api/pedidos/{pid}/lineas", headers=cab(camarero, k), json=cuerpo).json()
    dos = cliente.post(f"/api/pedidos/{pid}/lineas", headers=cab(camarero, k), json=cuerpo).json()

    assert len(uno["lineas"]) == len(dos["lineas"]) == 1
    assert uno["total_cent"] == dos["total_cent"]
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_la_respuesta_repetida_es_la_misma(cliente, camarero):
    """Lo que devuelve el reenvío es la respuesta de la primera vez, no una recalculada."""
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "llevar", "cliente": "Foto"}).json()["id"]
    k = clave()
    primera = cliente.post(f"/api/pedidos/{pid}/lineas", headers=cab(camarero, k),
                           json={"producto_id": 2, "cantidad": 1}).json()
    # entre medias pasa algo más: otra línea que la primera respuesta no puede conocer
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero, json={"producto_id": 15, "cantidad": 1})
    repetida = cliente.post(f"/api/pedidos/{pid}/lineas", headers=cab(camarero, k),
                            json={"producto_id": 2, "cantidad": 1}).json()

    assert repetida == primera
    assert len(cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["lineas"]) == 2
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_un_rechazo_no_se_guarda(cliente, camarero, encargado):
    """Un 409 no se congela: si la situación cambia, el reintento merece respuesta nueva.

    Aquí se pide un producto agotado y, tras reponerlo, la misma clave vuelve a intentarlo.
    """
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "llevar", "cliente": "Agotado"}).json()["id"]
    cliente.patch("/api/productos/2", headers=encargado, json={"disponible": False})

    k = clave()
    fallo = cliente.post(f"/api/pedidos/{pid}/lineas", headers=cab(camarero, k),
                         json={"producto_id": 2, "cantidad": 1})
    assert fallo.status_code == 409

    cliente.patch("/api/productos/2", headers=encargado, json={"disponible": True})
    bien = cliente.post(f"/api/pedidos/{pid}/lineas", headers=cab(camarero, k),
                        json={"producto_id": 2, "cantidad": 1})
    assert bien.status_code == 200 and len(bien.json()["lineas"]) == 1
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_clave_absurda(cliente, camarero):
    largo = "x" * 65
    r = cliente.post("/api/pedidos", headers=cab(camarero, largo), json={"tipo": "llevar"})
    assert r.status_code == 422


def test_la_clave_no_se_salta_los_permisos(cliente, cocina):
    """Repetir con clave no es una puerta trasera: quien no puede, sigue sin poder."""
    k = clave()
    for _ in range(2):
        assert cliente.post("/api/pedidos", headers=cab(cocina, k),
                            json={"tipo": "llevar"}).status_code == 403


# ─────────────── El reenvío completo de una tableta ───────────────
def test_reenvio_de_toda_la_libreta(cliente, camarero):
    """Lo que hace `sinred.js` al volver la red, y repetido entero como si se cayera a mitad.

    Secuencia real: abrir mesa, dos líneas, mandar a cocina. Se reenvía dos veces con las
    mismas claves y el resultado tiene que ser idéntico: un pedido, dos líneas, todo en cocina.
    """
    mesa = mesa_libre(cliente, camarero)["id"]
    libreta = [
        ("POST", "/api/pedidos", {"tipo": "sala", "mesa_id": mesa}, clave()),
        ("POST", "/api/pedidos/{pid}/lineas", {"producto_id": 2, "cantidad": 2}, clave()),
        ("POST", "/api/pedidos/{pid}/lineas", {"producto_id": 15, "cantidad": 1}, clave()),
        ("POST", "/api/pedidos/{pid}/enviar", None, clave()),
    ]

    pid = None
    for vuelta in (1, 2):
        for metodo, ruta, cuerpo, k in libreta:
            r = cliente.request(metodo, ruta.format(pid=pid), headers=cab(camarero, k), json=cuerpo)
            assert r.status_code == 200, r.text
            if pid is None:
                pid = r.json()["id"]
        assert pid is not None, f"vuelta {vuelta} sin pedido"

    final = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()
    assert len(final["lineas"]) == 2
    assert {l["estado"] for l in final["lineas"]} == {"enviada"}
    # y la mesa tiene UN pedido abierto, no dos: el segundo reenvío no abrió otro
    abiertos = [p for p in cliente.get("/api/mesas", headers=camarero).json() if p["id"] == mesa]
    assert abiertos[0]["pedido_id"] == pid
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)
