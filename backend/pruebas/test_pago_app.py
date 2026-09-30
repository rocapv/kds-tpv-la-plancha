"""Pagar desde el móvil del cliente. Lo que se vigila aquí es el dinero de otro.

Las dos reglas de `test_cuenta.py` siguen valiendo —**lo cobrado suma exactamente la cuenta**— y
se les añade una que solo aparece cuando el que cobra es un teléfono ajeno:

  · **De quién es el dinero lo dice el token, no el cuerpo.** Dos móviles en la misma mesa, cada
    uno con su token: ninguno puede pagar —ni dejar a medias— lo del otro.
  · **Repetir no cobra dos veces.** El wifi de un comedor se cae a mitad de petición y el teléfono
    reintenta. Con la misma `Idempotency-Key` el segundo intento devuelve el primer pago.
  · **El método lo pone el servidor.** Nunca «efectivo», porque de un teléfono no sale un billete.
"""
import uuid

import pytest

from conftest import mesa_libre

HAMBURGUESA = 2     # 10,50
AGUA = 14           # 2,00


@pytest.fixture
def sala(cliente, encargado, camarero):
    """Una mesa con pantalla y un móvil sentado: el cliente ha leído el QR y está dentro.

    `otro()` sienta un segundo teléfono con el código de unión, que es lo que hace el que llega
    tarde. Hacen falta dos para poder comprobar que ninguno paga lo del otro.
    """
    m = mesa_libre(cliente, camarero)
    alta = cliente.post("/api/pantallas", headers=encargado,
                        json={"mesa_id": m["id"], "nombre": "prueba pago"}).json()
    codigo = cliente.post("/api/pantalla/codigo",
                          headers={"X-Pantalla": alta["secreto"]}).json()["codigo"]
    v = cliente.post("/api/publico/mesa/canjear",
                     json={"codigo": codigo, "alias": "Ana"}).json()

    def otro(alias="Bruno"):
        r = cliente.post("/api/publico/mesa/unirse",
                         json={"codigo": v["codigo_union"], "alias": alias})
        assert r.status_code == 200, r.text
        return {"X-Visita": r.json()["token"]}

    yield {"mesa": m, "visita": v, "cab": {"X-Visita": v["token"]}, "otro": otro}

    # Se deja la mesa como estaba: pedido fuera, visita cerrada, pantalla de baja. Un pedido ya
    # cobrado no aparece en `/api/mesas`, así que no hay nada que anular.
    pedido = next((x["pedido_id"] for x in cliente.get("/api/mesas", headers=camarero).json()
                   if x["id"] == m["id"]), None)
    if pedido:
        cliente.post(f"/api/pedidos/{pedido}/anular", headers=camarero)
    cliente.post(f"/api/visitas/{v['id']}/cerrar", headers=camarero)
    cliente.delete(f"/api/pantallas/{alta['id']}", headers=encargado)


def _pedir(cliente, cab, producto=HAMBURGUESA, cantidad=1):
    r = cliente.post("/api/publico/visita/pedido", headers=cab,
                     json={"lineas": [{"producto_id": producto, "cantidad": cantidad}]})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["estado"] == "en cocina", d          # si se retiene, la prueba no mide lo que cree
    return d


def _comanda(cliente, cab):
    return cliente.get("/api/publico/visita/comanda", headers=cab).json()


def _pagar(cliente, cab=None, **cuerpo):
    """Sin `cab` se paga sin cabecera de mesa: es el caso del que no ha leído ningún QR."""
    return cliente.post("/api/publico/visita/pagar", headers=cab, json=cuerpo)


def _clave():
    """Una `Idempotency-Key` distinta por acción, que es como la inventa el teléfono."""
    return {"Idempotency-Key": uuid.uuid4().hex}


# ─────────────── Lo mío y lo de la mesa ───────────────
def test_pagar_lo_mio_deja_el_resto_de_la_mesa_pendiente(cliente, sala):
    bruno = sala["otro"]()
    _pedir(cliente, sala["cab"])
    _pedir(cliente, bruno, AGUA, 2)
    mio = _comanda(cliente, sala["cab"])["mio"]

    r = _pagar(cliente, sala["cab"])
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["importe_cent"] == mio["a_pagar_cent"] > 0
    assert not d["cuenta_saldada"] and d["saldo_cent"] > 0
    # Y lo que queda es exactamente lo de Bruno
    assert d["saldo_cent"] == _comanda(cliente, bruno)["mio"]["a_pagar_cent"]


def test_pagar_todo_salda_la_cuenta_y_cierra_el_pedido(cliente, camarero, sala):
    pid = _pedir(cliente, sala["cab"], AGUA, 3)["pedido_id"]
    total = _comanda(cliente, sala["cab"])["total_cent"]

    d = _pagar(cliente, sala["cab"], todo=True).json()
    assert d["importe_cent"] == total and d["cuenta_saldada"] and d["saldo_cent"] == 0
    p = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()
    assert p["estado"] == "cobrado"
    assert sum(g["importe_cent"] for g in p["pagos"]) == total     # ni de más ni de menos
    assert all(l["pago_id"] for l in p["lineas"] if l["estado"] != "anulada")


def test_el_metodo_es_app_aunque_el_telefono_pida_otro(cliente, camarero, sala):
    """Desde un móvil no se paga en efectivo: dejarlo elegir es dejarle vaciar el cajón a mano."""
    pid = _pedir(cliente, sala["cab"], AGUA, 1)["pedido_id"]
    r = _pagar(cliente, sala["cab"], todo=True, metodo="efectivo", entregado_cent=100000)
    assert r.status_code == 201, r.text
    pagos = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["pagos"]
    assert [g["metodo"] for g in pagos] == ["app"]
    assert pagos[0]["entregado_cent"] is None and pagos[0]["cambio_cent"] is None


def test_un_movil_no_paga_lo_del_de_al_lado(cliente, camarero, sala):
    """Lo de cada uno se sabe por el token. Y al final la suma es la cuenta, como siempre."""
    bruno = sala["otro"]()
    pid = _pedir(cliente, sala["cab"])["pedido_id"]
    _pedir(cliente, bruno, AGUA, 2)
    total = _comanda(cliente, sala["cab"])["total_cent"]

    primero = _pagar(cliente, sala["cab"]).json()
    # Pagar Ana no toca lo de Bruno: sigue debiendo lo suyo y sin marcar como pagado
    suyo = _comanda(cliente, bruno)["mio"]
    assert not suyo["pagado"] and suyo["a_pagar_cent"] > 0
    segundo = _pagar(cliente, bruno).json()

    assert primero["importe_cent"] + segundo["importe_cent"] == total
    p = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()
    assert p["estado"] == "cobrado"
    assert len({g["comensal_id"] for g in p["pagos"]}) == 2      # dos personas, dos cobros


def test_mandar_el_comensal_de_otro_no_sirve_de_nada(cliente, camarero, sala):
    """El ataque que esta ruta tiene que aguantar: pagar lo de otro cambiando un número.

    Ana pide una hamburguesa (10,50) y Bruno dos aguas (4,00). Si el comensal viniera en el cuerpo,
    Ana podría mandar el de Bruno y saldar lo de Bruno —o dejarlo a medias— desde su teléfono. El
    comensal sale del token, así que a Ana se le cobra lo de Ana y ya está.
    """
    bruno = sala["otro"]()
    _pedir(cliente, sala["cab"])
    _pedir(cliente, bruno, AGUA, 2)
    suyo_ana = _comanda(cliente, sala["cab"])["mio"]
    suyo_bruno = _comanda(cliente, bruno)["mio"]
    assert suyo_ana["a_pagar_cent"] != suyo_bruno["a_pagar_cent"]      # si no, no se distinguiría

    d = _pagar(cliente, sala["cab"], comensal_id=suyo_bruno["comensal_id"],
               concepto="Bruno", importe_cent=1).json()
    assert d["importe_cent"] == suyo_ana["a_pagar_cent"]
    assert d["concepto"] == "Ana"
    # Y a Bruno no le han tocado la cuenta
    despues = _comanda(cliente, bruno)["mio"]
    assert not despues["pagado"] and despues["a_pagar_cent"] == suyo_bruno["a_pagar_cent"]


def test_el_que_no_pidio_nada_paga_su_parte_de_lo_del_centro(cliente, camarero, sala):
    """Dos sentados y una botella que trajo el camarero: se parte, y la caja cuadra."""
    bruno = sala["otro"]()
    pid = _pedir(cliente, sala["cab"])["pedido_id"]
    _pedir(cliente, bruno, HAMBURGUESA, 1)
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                 json={"producto_id": AGUA, "cantidad": 1})       # de la mesa, sin dueño
    cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
    total = _comanda(cliente, sala["cab"])["total_cent"]

    pagados = [_pagar(cliente, cab).json()["importe_cent"] for cab in (sala["cab"], bruno)]
    assert sum(pagados) == total
    assert max(pagados) - min(pagados) <= 1        # nadie paga la botella entera por ir primero
    assert cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["estado"] == "cobrado"


# ─────────────── El wifi del comedor ───────────────
def test_reenviar_la_misma_clave_devuelve_el_mismo_pago(cliente, camarero, sala):
    """El teléfono reintenta porque no sabe si llegó, y tiene que salirle el recibo, no un error.

    Cobrar dos veces no podría: la cuenta ya lo impide (`cobro_de` no cobra a quien pagó). Lo que
    se gana aquí es la RESPUESTA: sin la clave, el reintento recibe un 409 «Ana ya ha pagado lo
    suyo» y el cliente se queda mirando un error después de haber pagado de verdad.
    """
    bruno = sala["otro"]()
    pid = _pedir(cliente, sala["cab"])["pedido_id"]
    _pedir(cliente, bruno, AGUA, 2)                 # así la cuenta sigue abierta tras cobrar a Ana
    clave = _clave()

    primero = cliente.post("/api/publico/visita/pagar", headers={**sala["cab"], **clave}, json={})
    repetido = cliente.post("/api/publico/visita/pagar", headers={**sala["cab"], **clave}, json={})
    assert primero.status_code == repetido.status_code == 201
    assert repetido.json() == primero.json()
    assert repetido.headers.get("X-Idempotencia") == "repetida"
    assert len(cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["pagos"]) == 1


def test_con_clave_nueva_tampoco_se_le_cobra_otra_vez(cliente, camarero, sala):
    """La idempotencia cubre el reintento; que no se cobre dos veces a la misma persona lo cubre
    la cuenta. Son dos guardas distintas y las dos tienen que estar: con una clave nueva la
    primera no se entera, y aun así Ana no vuelve a pagar."""
    bruno = sala["otro"]()
    pid = _pedir(cliente, sala["cab"])["pedido_id"]
    _pedir(cliente, bruno, AGUA, 2)                 # la mesa sigue debiendo, pero Ana ya no
    assert cliente.post("/api/publico/visita/pagar", headers={**sala["cab"], **_clave()},
                        json={}).status_code == 201
    r = cliente.post("/api/publico/visita/pagar", headers={**sala["cab"], **_clave()}, json={})
    assert r.status_code == 409 and "ya ha pagado lo suyo" in r.json()["detail"]
    assert len(cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["pagos"]) == 1


# ─────────────── Cuándo no se deja pagar ───────────────
def test_algo_sin_confirmar_para_el_pago(cliente, camarero, sala):
    """Una línea apuntada en el TPV y sin enviar: cobrar ahora deja la cuenta corta."""
    pid = _pedir(cliente, sala["cab"])["pedido_id"]
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                 json={"producto_id": AGUA, "cantidad": 1})       # se queda 'pendiente'
    r = _pagar(cliente, sala["cab"], todo=True)
    assert r.status_code == 409
    assert "camarero" in r.json()["detail"] and "pendiente" not in r.json()["detail"]


def test_sin_pedido_no_hay_nada_que_pagar(cliente, sala):
    r = _pagar(cliente, sala["cab"])
    assert r.status_code == 409 and r.json()["detail"] == "Todavía no hay nada que pagar en esta mesa"


def test_la_mesa_abierta_y_sin_nada_apuntado_no_dice_que_ya_pagaste(cliente, camarero, encargado):
    """El camarero abre la mesa, el cliente lee el QR y toca «Pagar» mientras espera la carta.

    El saldo es cero y la comprobación de saldo, sola, le contestaba «Esta cuenta ya está pagada»:
    una mentira que le hace creer que ha pagado algo.
    """
    m = mesa_libre(cliente, camarero)
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": m["id"]}).json()["id"]
    alta = cliente.post("/api/pantallas", headers=encargado,
                        json={"mesa_id": m["id"], "nombre": "prueba vacía"}).json()
    try:
        codigo = cliente.post("/api/pantalla/codigo",
                              headers={"X-Pantalla": alta["secreto"]}).json()["codigo"]
        v = cliente.post("/api/publico/mesa/canjear", json={"codigo": codigo}).json()
        assert v["pedido_id"] == pid              # la visita nace enganchada al pedido del camarero
        r = _pagar(cliente, {"X-Visita": v["token"]})
        assert r.status_code == 409
        assert r.json()["detail"] == "Todavía no hay nada que pagar en esta mesa"
    finally:
        cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)
        cliente.post(f"/api/visitas/{v['id']}/cerrar", headers=camarero)
        cliente.delete(f"/api/pantallas/{alta['id']}", headers=encargado)


def test_la_cuenta_saldada_se_dice_en_palabras_de_cliente(cliente, sala):
    _pedir(cliente, sala["cab"], AGUA, 1)
    assert _pagar(cliente, sala["cab"], todo=True).status_code == 201
    r = _pagar(cliente, sala["cab"], todo=True)
    assert r.status_code == 409
    # Ni «El pedido está cobrado» ni nada con la palabra «pedido»: eso es jerga del TPV
    assert r.json()["detail"] == "Esta cuenta ya está pagada"


def test_sin_el_codigo_de_la_mesa_no_se_paga(cliente, sala):
    _pedir(cliente, sala["cab"], AGUA, 1)
    assert _pagar(cliente).status_code == 401
    assert cliente.post("/api/publico/visita/pagar", headers={"X-Visita": "x" * 64},
                        json={}).status_code == 401


# ─────────────── La caja ───────────────
def test_el_arqueo_no_mete_la_app_en_el_cajon(cliente, camarero, sala):
    """Un cobro desde el móvil no deja un billete: si contara como efectivo, el cierre Z pediría
    cuadrar a ciegas un dinero que no está."""
    antes = cliente.get("/api/arqueo", headers=camarero).json()
    _pedir(cliente, sala["cab"], AGUA, 2)
    importe = _pagar(cliente, sala["cab"], todo=True).json()["importe_cent"]

    despues = cliente.get("/api/arqueo", headers=camarero).json()
    assert despues["ventas_efectivo_cent"] == antes["ventas_efectivo_cent"]
    assert despues["esperado_cent"] == antes["esperado_cent"]
    assert despues["ventas_total_cent"] == antes["ventas_total_cent"] + importe
    # pero se ve, con su nombre y separado de la tarjeta
    app = next(f for f in despues["por_metodo"] if f["metodo"] == "app")
    assert int(app["total_cent"]) >= importe


# ─────────────── Lo que le toca a este teléfono ───────────────
def test_la_comanda_dice_lo_suyo_solo_si_ha_pedido(cliente, sala):
    """Sin platos a su nombre no hay forma honrada de decirle cuánto es «lo suyo»: va `null`."""
    bruno = sala["otro"]()
    _pedir(cliente, sala["cab"])
    assert _comanda(cliente, bruno)["mio"] is None

    mio = _comanda(cliente, sala["cab"])["mio"]
    assert mio["nombre"] == "Ana" and not mio["pagado"]
    assert mio["a_pagar_cent"] == mio["suyo_cent"] + mio["compartido_cent"] > 0


def test_despues_de_pagar_lo_suyo_queda_marcado(cliente, sala):
    sala["otro"]()
    _pedir(cliente, sala["cab"])
    _pagar(cliente, sala["cab"])
    mio = _comanda(cliente, sala["cab"])["mio"]
    assert mio["pagado"] and mio["a_pagar_cent"] == 0
