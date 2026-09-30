"""La factura a petición: de qué parte de la cuenta es, quién la pide y hasta cuándo sale sola.

Tres cosas se comprueban aquí una y otra vez, porque son las que no se pueden romper:

  · **La suma de los justificantes es la cuenta.** O una factura por cabeza, o una de todos.
    Las dos a la vez sería cobrar dos veces lo mismo sobre el papel.
  · **Un ticket, una factura.** Pulsar dos veces devuelve la primera, nunca un número nuevo.
  · **«Ya no se puede» no es una respuesta.** Con la caja cerrada la app deja de emitir, pero lo
    que contesta es a quién pedirla; y el encargado la sigue emitiendo, que es lo que manda el
    reglamento de facturación.
"""
from datetime import date

import pytest

from conftest import mesa_libre

AGUA = 14           # 2,00
HAMBURGUESA = 2     # 10,50


# ─────────────── La caja del día, que aquí es una precondición ───────────────
# `facturacion.plazo()` mira el arqueo de hoy, y `test_arqueo.py` firma el cierre Z —que para eso
# es un cierre: no tiene vuelta atrás— antes de que pytest llegue a este fichero. Una prueba de
# facturas que dependa de qué ficheros se han ejecutado antes no prueba nada, así que el estado de
# la caja se pone a mano en cada prueba y se devuelve como estaba al salir.
def _db():
    """`app.db` importado **dentro** de la función, nunca arriba.

    `db.CFG` se construye al importar el módulo, leyendo el entorno. Un import al principio del
    fichero se ejecuta al recolectar, antes de que `conftest` apunte a `kds_tpv_test`: las pruebas
    escribirían en la base de datos **de producción**.
    """
    from app import db
    return db


def _caja(estado: str) -> str | None:
    """Pone la caja de hoy en ese estado y devuelve el que tenía (None si no había caja).

    Se escribe en la tabla a pelo, y a propósito: **no hay ni debe haber una puerta para reabrir un
    cierre Z**, sería un agujero contable. Aquí hace falta porque la prueba necesita las dos
    situaciones, y la base de pruebas se crea y se destruye con la sesión.
    """
    db = _db()
    hoy = date.today().isoformat()
    antes = db.q1("SELECT estado FROM arqueos WHERE fecha=%s", (hoy,))
    if antes:
        db.q("UPDATE arqueos SET estado=%s WHERE fecha=%s", (estado, hoy))
    else:
        jefe = db.q1("SELECT id FROM empleados ORDER BY id LIMIT 1")["id"]
        db.q("INSERT INTO arqueos (fecha, estado, abierto_por) VALUES (%s,%s,%s)",
             (hoy, estado, jefe))
    return antes["estado"] if antes else None


def _devolver_caja(estado: str | None) -> None:
    db = _db()
    hoy = date.today().isoformat()
    if estado is None:
        db.q("DELETE FROM arqueos WHERE fecha=%s", (hoy,))
    else:
        db.q("UPDATE arqueos SET estado=%s WHERE fecha=%s", (estado, hoy))


@pytest.fixture(autouse=True)
def caja_abierta(base_de_pruebas):
    """Servicio en marcha: la caja de hoy abierta, que es cuando la app emite sola."""
    previo = _caja("abierto")
    yield
    _devolver_caja(previo)


@pytest.fixture
def caja_cerrada(caja_abierta):
    """El día ya firmado. A partir de aquí la factura la hace el encargado, no la app."""
    _caja("cerrado")
    yield


def _mover_al_dia_anterior(pedido_id: int) -> None:
    """Deja la operación con fecha de ayer.

    Es la única manera de probar «esa cuenta es de otro día»: una prueba no puede esperar a mañana.
    Se mueven el cierre del pedido y sus cobros, que son las dos fechas que mira el plazo.
    """
    db = _db()
    db.q("UPDATE pedidos SET cerrado_en = cerrado_en - INTERVAL 1 DAY WHERE id=%s", (pedido_id,))
    db.q("UPDATE pagos SET pagado_en = pagado_en - INTERVAL 1 DAY WHERE pedido_id=%s", (pedido_id,))


# ─────────────── La mesa y sus teléfonos ───────────────
@pytest.fixture
def mesa(cliente, encargado, camarero):
    """Mesa con pantalla, QR leído y visita abierta: dos teléfonos pueden sentarse en ella."""
    m = mesa_libre(cliente, camarero)
    alta = cliente.post("/api/pantallas", headers=encargado,
                        json={"mesa_id": m["id"], "nombre": "prueba factura"}).json()
    codigo = cliente.post("/api/pantalla/codigo",
                          headers={"X-Pantalla": alta["secreto"]}).json()["codigo"]
    v = cliente.post("/api/publico/mesa/canjear",
                     json={"codigo": codigo, "alias": "Ana"}).json()
    yield {"mesa": m, "visita": v, "cab": {"X-Visita": v["token"]},
           "union": v["codigo_union"], "pantalla": alta["id"]}
    # La mesa se deja como estaba. Un pedido ya cobrado no sale en `/api/mesas`, así que solo hay
    # que anular lo que quede abierto.
    pedido = next((x["pedido_id"] for x in cliente.get("/api/mesas", headers=camarero).json()
                   if x["id"] == m["id"]), None)
    if pedido:
        cliente.post(f"/api/pedidos/{pedido}/anular", headers=camarero)
    cliente.post(f"/api/visitas/{v['id']}/cerrar", headers=camarero)
    cliente.delete(f"/api/pantallas/{alta['id']}", headers=encargado)


def _segundo_telefono(cliente, mesa, alias="Bruno"):
    """Otro comensal en la misma mesa, por el código de unión: el que llega tarde."""
    r = cliente.post("/api/publico/mesa/unirse",
                     json={"codigo": mesa["union"], "alias": alias})
    assert r.status_code == 200, r.text
    return {"X-Visita": r.json()["token"]}


def _pide(cliente, cab, producto, cantidad=1):
    r = cliente.post("/api/publico/visita/pedido", headers=cab,
                     json={"lineas": [{"producto_id": producto, "cantidad": cantidad}]})
    assert r.status_code == 201, r.text
    d = r.json()
    # Si el pedido se retiene a la espera de un camarero no hay líneas en la mesa y la prueba
    # mediría otra cosa.
    assert d["estado"] == "en cocina", d
    return d


def _compartido(cliente, camarero, pedido_id, producto, cantidad=1):
    """Una línea sin dueño: el agua del centro de la mesa.

    Lo compartido es lo que apunta el camarero en el TPV, porque lo que se pide desde un móvil
    queda a nombre de ese móvil. Hay que enviarlo a cocina: con líneas sin confirmar, la app no
    deja pagar.
    """
    r = cliente.post(f"/api/pedidos/{pedido_id}/lineas", headers=camarero,
                     json={"producto_id": producto, "cantidad": cantidad})
    assert r.status_code in (200, 201), r.text
    cliente.post(f"/api/pedidos/{pedido_id}/enviar", headers=camarero)


def _paga(cliente, cab, **cuerpo):
    r = cliente.post("/api/publico/visita/pagar", headers=cab, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _factura(cliente, cab, **cuerpo):
    return cliente.post("/api/publico/visita/factura", headers=cab, json=cuerpo)


@pytest.fixture
def contacto_del_local(cliente, encargado):
    """Teléfono y correo puestos, porque son la respuesta cuando la app no puede emitir."""
    antes = cliente.get("/api/ajustes", headers=encargado).json()
    for clave, valor in (("local_telefono", "960 12 34 56"),
                         ("local_email", "facturas@ejemplo.es")):
        assert cliente.put(f"/api/ajustes/{clave}", headers=encargado,
                           json={"valor": valor}).status_code == 200
    yield {"telefono": "960 12 34 56", "email": "facturas@ejemplo.es"}
    for clave in ("local_telefono", "local_email"):
        cliente.put(f"/api/ajustes/{clave}", headers=encargado,
                    json={"valor": antes.get(clave) or ""})


# ─────────────── Lo que pide el cliente desde la mesa ───────────────
def test_quien_paga_lo_suyo_saca_la_factura_de_lo_suyo(cliente, mesa):
    """La factura de Ana dice lo que puso Ana, no lo que cenaron los cuatro."""
    otro = _segundo_telefono(cliente, mesa)
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, otro, AGUA, 2)
    pago = _paga(cliente, mesa["cab"], con_compartido=False)

    r = _factura(cliente, mesa["cab"], alcance="mio")
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["total_cent"] == pago["importe_cent"]
    assert f["alcance"] == "mio" and f["numero_completo"].startswith("A")
    # La cuenta de la mesa sigue abierta: Bruno no ha pagado y eso no impide la factura de Ana.
    assert f["base_cent"] + f["iva_cent"] == f["total_cent"]


def test_el_detalle_de_la_factura_suma_el_total(cliente, camarero, mesa):
    """Con lo compartido, las líneas de uno no suman lo que puso: la diferencia va escrita.

    Es la trampa de este reparto: las líneas compartidas no se marcan con su pago porque siguen
    abiertas para los demás. En un ticket se puede disimular; en una factura, no: la suma del
    detalle tiene que ser el total o el documento está mal hecho.
    """
    otro = _segundo_telefono(cliente, mesa)
    pid = _pide(cliente, mesa["cab"], HAMBURGUESA)["pedido_id"]     # de Ana
    _pide(cliente, otro, HAMBURGUESA)                               # de Bruno
    _compartido(cliente, camarero, pid, AGUA, 2)                    # del centro
    pago = _paga(cliente, mesa["cab"], con_compartido=True)

    f = _factura(cliente, mesa["cab"], alcance="mio").json()
    assert f["total_cent"] == pago["importe_cent"] > 1050           # su plato y parte del agua
    assert sum(l["importe_cent"] for l in f["lineas"]) == f["total_cent"]
    assert any("compart" in l["producto"] for l in f["lineas"])


def test_con_nif_sale_completa(cliente, mesa):
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    f = _factura(cliente, mesa["cab"], alcance="mesa", nif="12345678Z",
                 nombre="Ana Pérez", direccion="Calle Falsa 1").json()
    assert f["tipo"] == "completa" and f["cliente_nif"] == "12345678Z"
    assert f["local"]["nif"] and f["local"]["nombre"]


def test_sin_nif_no_se_niega_la_factura_sale_la_simplificada(cliente, mesa):
    """Pedirla sin datos fiscales no es un error: el ticket de siempre ya es una factura."""
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    f = _factura(cliente, mesa["cab"], alcance="mesa").json()
    assert f["tipo"] == "simplificada" and f["total_cent"] > 0


def test_pulsar_dos_veces_no_emite_dos_facturas(cliente, mesa):
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    una = _factura(cliente, mesa["cab"], alcance="mesa").json()
    dos = _factura(cliente, mesa["cab"], alcance="mesa").json()
    assert una["id"] == dos["id"] and una["numero_completo"] == dos["numero_completo"]


def test_la_factura_del_cliente_no_lleva_nada_de_dentro(cliente, mesa):
    """Tiene derecho a su factura, no al parte de trabajo del local."""
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _paga(cliente, mesa["cab"], todo=True)
    f = _factura(cliente, mesa["cab"], alcance="mesa").json()
    plano = repr(f)
    assert "camarero" not in plano and "estacion" not in plano
    assert "empleado_id" not in plano and "secreto" not in plano


def test_la_factura_es_de_un_cobro_o_de_la_cuenta_y_no_de_lo_que_diga_el_cuerpo(cliente, mesa):
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    assert _factura(cliente, mesa["cab"], alcance="la mesa de al lado").status_code == 422


# ─────────────── La regla que no se puede romper ───────────────
def test_o_una_por_cabeza_o_una_de_todos(cliente, mesa):
    """Con una factura por cabeza emitida, la de la cuenta entera cobraría dos veces lo mismo."""
    otro = _segundo_telefono(cliente, mesa)
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, otro, AGUA)
    _paga(cliente, mesa["cab"], con_compartido=False)
    assert _factura(cliente, mesa["cab"], alcance="mio").status_code == 201
    _paga(cliente, otro, con_compartido=True)          # Bruno salda el resto

    r = _factura(cliente, otro, alcance="mesa")
    assert r.status_code == 409 and "por cabeza" in r.json()["detail"]


def test_con_factura_de_la_mesa_ya_no_hay_por_cabeza(cliente, mesa):
    otro = _segundo_telefono(cliente, mesa)
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, otro, AGUA)
    _paga(cliente, mesa["cab"], con_compartido=False)
    _paga(cliente, otro, con_compartido=True)
    assert _factura(cliente, otro, alcance="mesa").status_code == 201
    r = _factura(cliente, mesa["cab"], alcance="mio")
    assert r.status_code == 409 and "cuenta entera" in r.json()["detail"]


def test_no_se_factura_la_mesa_a_medio_pagar(cliente, mesa):
    otro = _segundo_telefono(cliente, mesa)
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, otro, AGUA)
    _paga(cliente, mesa["cab"], con_compartido=False)
    r = _factura(cliente, otro, alcance="mesa")
    assert r.status_code == 409 and "saldada" in r.json()["detail"]


def test_sin_haber_pagado_no_hay_factura_propia(cliente, mesa):
    _pide(cliente, mesa["cab"], AGUA)
    r = _factura(cliente, mesa["cab"], alcance="mio")
    assert r.status_code == 409 and "pagado" in r.json()["detail"]


def test_un_cobro_con_factura_ya_no_se_puede_borrar(cliente, camarero, mesa):
    """Borrar el cobro dejaría un número de factura sin operación detrás.

    Hacen falta tres en la mesa: un pago solo se deshace con el pedido abierto, así que Carla se
    queda sin pagar para que la cuenta no se cierre y se pueda comprobar también lo contrario.
    """
    bruno = _segundo_telefono(cliente, mesa)
    carla = _segundo_telefono(cliente, mesa, "Carla")
    pid = _pide(cliente, mesa["cab"], HAMBURGUESA)["pedido_id"]
    _pide(cliente, bruno, AGUA)
    _pide(cliente, carla, AGUA)
    pago = _paga(cliente, mesa["cab"], con_compartido=False)
    assert _factura(cliente, mesa["cab"], alcance="mio").status_code == 201

    r = cliente.delete(f"/api/pedidos/{pid}/pagos/{pago['pago_id']}", headers=camarero)
    assert r.status_code == 409 and "rectificarla" in r.json()["detail"]
    # Y sin factura sí se deshace, que es para lo que está: un error de caja reciente.
    suyo = _paga(cliente, bruno, con_compartido=False)
    assert cliente.delete(f"/api/pedidos/{pid}/pagos/{suyo['pago_id']}",
                          headers=camarero).status_code == 200


# ─────────────── El plazo ───────────────
def test_de_otro_dia_la_app_dice_a_quien_pedirla_y_el_encargado_la_emite(
        cliente, camarero, encargado, mesa, contacto_del_local):
    """No dice «no se puede»: dice el teléfono y el correo del local.

    Es la corrección al encargo original. El plazo de facturación no termina al bajar la persiana,
    y contestarle al cliente que ya es imposible es lo que acaba en reclamación. La factura de una
    operación de otro día la emite el encargado —mueve un arqueo que alguien dio por bueno— y el
    documento lleva las dos fechas, la de la operación y la de expedición.
    """
    pid = _pide(cliente, mesa["cab"], AGUA)["pedido_id"]
    _paga(cliente, mesa["cab"], todo=True)
    _mover_al_dia_anterior(pid)

    r = _factura(cliente, mesa["cab"], alcance="mesa")
    assert r.status_code == 409
    detalle = r.json()["detail"]
    assert contacto_del_local["telefono"] in detalle
    assert contacto_del_local["email"] in detalle
    assert "obligados" in detalle

    # Y la sala tampoco la deja a un camarero: mueve un arqueo que ya está cerrado.
    rc = cliente.post(f"/api/pedidos/{pid}/factura", headers=camarero, json={})
    assert rc.status_code == 403 and "encargado" in rc.json()["detail"]

    # El encargado sí, que es la salida que pide el reglamento.
    re_ = cliente.post(f"/api/pedidos/{pid}/factura", headers=encargado,
                       json={"tipo": "completa", "cliente_nif": "12345678Z",
                             "cliente_nombre": "Ana Pérez"})
    assert re_.status_code == 201, re_.text
    f = re_.json()
    assert f["tipo"] == "completa" and f["fuera_de_fecha"] is True
    assert f["operacion_en"][:10] != f["emitida_en"][:10]


def test_con_la_caja_del_dia_cerrada_la_app_no_emite(cliente, mesa, caja_cerrada,
                                                     contacto_del_local):
    """Firmado el cierre Z, la app deja de emitir: cambiaría un arqueo ya cuadrado."""
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    r = _factura(cliente, mesa["cab"], alcance="mesa")
    assert r.status_code == 409
    assert "caja" in r.json()["detail"] and contacto_del_local["telefono"] in r.json()["detail"]
    # Y la pantalla lo sabe antes de pintar el botón.
    ve = cliente.get("/api/publico/visita/factura", headers=mesa["cab"]).json()
    assert not ve["puedo_pedirla"] and ve["alcance_sugerido"] is None
    assert not ve["plazo"]["abierto"] and ve["plazo"]["como_pedirla"]


def test_se_puede_apagar_la_factura_desde_la_app(cliente, encargado, mesa):
    """Un interruptor en ajustes, para apagarlo sin tocar el TPV."""
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    cliente.put("/api/ajustes/factura_app", headers=encargado, json={"valor": "no"})
    try:
        r = _factura(cliente, mesa["cab"], alcance="mesa")
        assert r.status_code == 409 and "Llama" in r.json()["detail"]
        assert not cliente.get("/api/publico/visita/factura",
                               headers=mesa["cab"]).json()["puedo_pedirla"]
    finally:
        cliente.put("/api/ajustes/factura_app", headers=encargado, json={"valor": "si"})


# ─────────────── Lo que ve la pantalla antes de ofrecer el botón ───────────────
def test_la_pantalla_no_ofrece_un_boton_que_va_a_fallar(cliente, mesa):
    """`puedo_pedirla` no es «la caja está abierta»: es «si pulsas, sale factura»."""
    _pide(cliente, mesa["cab"], AGUA)
    antes = cliente.get("/api/publico/visita/factura", headers=mesa["cab"]).json()
    assert antes["mia"] is None and antes["de_la_mesa"] is None
    assert not antes["puedo_pedirla"] and antes["alcance_sugerido"] is None

    _paga(cliente, mesa["cab"], todo=True)
    despues = cliente.get("/api/publico/visita/factura", headers=mesa["cab"]).json()
    assert despues["cuenta_saldada"] and despues["puedo_pedirla"]
    assert despues["alcance_sugerido"] == "mesa"

    _factura(cliente, mesa["cab"], alcance="mesa")
    final = cliente.get("/api/publico/visita/factura", headers=mesa["cab"]).json()
    assert final["de_la_mesa"]["numero_completo"]
    assert not final["puedo_pedirla"] and final["alcance_sugerido"] is None


def test_cuando_no_se_puede_dice_cual_de_los_dos_noes_es(cliente, mesa, contacto_del_local):
    """Hay dos «noes» y la pantalla no puede confundirlos.

    Uno es el del plazo —la app no, el local sí, y ahí va su teléfono—. El otro es el de la regla
    de «una por cabeza o una de todos», donde el teléfono sobra: el local tampoco va a hacerle una
    segunda factura de lo mismo. Sin `al_local`, la pantalla enseñaba «Llama al…» en los dos.
    """
    bruno = _segundo_telefono(cliente, mesa)
    carla = _segundo_telefono(cliente, mesa, "Carla")     # mira la cuenta y no paga nunca
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, bruno, AGUA)

    # Carla no ha pagado y la cuenta sigue abierta: ni se puede, ni es cosa del local.
    ve = cliente.get("/api/publico/visita/factura", headers=carla).json()
    assert not ve["puedo_pedirla"] and ve["al_local"] is False
    assert "no has pagado" in ve["motivo"]
    assert contacto_del_local["telefono"] not in ve["motivo"]

    # Ana paga lo suyo y saca su factura; Bruno salda el resto. Con una factura por cabeza ya
    # emitida, la de la cuenta entera que querría Carla no se puede hacer: ni aquí ni llamando.
    _paga(cliente, mesa["cab"], con_compartido=False)
    assert _factura(cliente, mesa["cab"], alcance="mio").status_code == 201
    _paga(cliente, bruno, con_compartido=True)
    ve = cliente.get("/api/publico/visita/factura", headers=carla).json()
    assert ve["cuenta_saldada"] and not ve["puedo_pedirla"] and ve["al_local"] is False
    assert ve["por_cabeza"] == 1 and "de quien pagó su parte" in ve["motivo"]
    assert "la cuenta entera" in ve["motivo"]


def test_con_la_caja_cerrada_el_no_si_lleva_el_telefono(cliente, mesa, caja_cerrada,
                                                        contacto_del_local):
    """El otro «no»: aquí el local sí puede, y el motivo va con a quién llamar."""
    _pide(cliente, mesa["cab"], AGUA)
    _paga(cliente, mesa["cab"], todo=True)
    ve = cliente.get("/api/publico/visita/factura", headers=mesa["cab"]).json()
    assert not ve["puedo_pedirla"] and ve["al_local"] is True
    assert "caja" in ve["motivo"] and contacto_del_local["telefono"] in ve["plazo"]["como_pedirla"]


def test_sin_mesa_no_se_pide_factura(cliente):
    assert cliente.post("/api/publico/visita/factura", json={"alcance": "mesa"}).status_code == 401
    assert cliente.get("/api/publico/visita/factura").status_code == 401


# ─────────────── Perfil: «factúrame siempre» ───────────────
def _cuenta(cliente, correo, contrasena, nombre):
    r = cliente.post("/api/publico/clientes/registro",
                     json={"email": correo, "contrasena": contrasena, "nombre": nombre})
    if r.status_code == 409:
        r = cliente.post("/api/publico/clientes/entrar",
                         json={"email": correo, "contrasena": contrasena})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture
def cuenta_con_factura_auto(cliente):
    cab = _cuenta(cliente, "factura.auto@ejemplo.es", "unaclavelarga", "Ana")
    cliente.patch("/api/publico/clientes/yo", headers=cab,
                  json={"nif": "87654321X", "razon_social": "Talleres Ana SL",
                        "direccion": "Polígono 3", "factura_auto": True})
    yield cab
    cliente.patch("/api/publico/clientes/yo", headers=cab, json={"factura_auto": False})


def test_facturame_siempre_no_pregunta_nada(cliente, encargado, camarero,
                                            cuenta_con_factura_auto):
    """Quien lo dejó puesto en su perfil recibe la factura con el propio pago."""
    m = mesa_libre(cliente, camarero)
    alta = cliente.post("/api/pantallas", headers=encargado,
                        json={"mesa_id": m["id"], "nombre": "auto"}).json()
    codigo = cliente.post("/api/pantalla/codigo",
                          headers={"X-Pantalla": alta["secreto"]}).json()["codigo"]
    v = cliente.post("/api/publico/mesa/canjear", json={"codigo": codigo, "alias": "Ana"},
                     headers=cuenta_con_factura_auto).json()
    cab = {"X-Visita": v["token"]}
    try:
        _pide(cliente, cab, HAMBURGUESA)
        pago = _paga(cliente, cab, todo=True)
        assert pago["factura"], "con factura_auto la factura tiene que salir sola"
        f = pago["factura"]
        assert f["tipo"] == "completa" and f["cliente_nif"] == "87654321X"
        assert f["cliente_nombre"] == "Talleres Ana SL"
        assert f["total_cent"] == pago["importe_cent"]
        assert sum(l["importe_cent"] for l in f["lineas"]) == f["total_cent"]

        # Y aparece en «mis facturas», que es lo único que enlaza factura y cuenta de cliente.
        mias = cliente.get("/api/publico/clientes/facturas",
                           headers=cuenta_con_factura_auto).json()
        assert any(x["id"] == f["id"] for x in mias)
        suelta = cliente.get(f"/api/publico/clientes/facturas/{f['id']}",
                             headers=cuenta_con_factura_auto)
        assert suelta.status_code == 200 and suelta.json()["id"] == f["id"]
    finally:
        pedido = next((x["pedido_id"] for x in cliente.get("/api/mesas", headers=camarero).json()
                       if x["id"] == m["id"]), None)
        if pedido:
            cliente.post(f"/api/pedidos/{pedido}/anular", headers=camarero)
        cliente.post(f"/api/visitas/{v['id']}/cerrar", headers=camarero)
        cliente.delete(f"/api/pantallas/{alta['id']}", headers=encargado)


def test_las_facturas_de_otro_no_se_ven(cliente, cuenta_con_factura_auto):
    """Se filtra por cuenta, no por NIF: dos de la misma empresa no comparten cenas."""
    otro = _cuenta(cliente, "otra.persona@ejemplo.es", "otraclavelarga", "Bruno")
    mias = cliente.get("/api/publico/clientes/facturas",
                       headers=cuenta_con_factura_auto).json()
    if mias:
        r = cliente.get(f"/api/publico/clientes/facturas/{mias[0]['id']}", headers=otro)
        assert r.status_code == 404          # 404 y no 403: un 403 confirmaría que existe
    assert cliente.get("/api/publico/clientes/facturas").status_code == 401


# ─────────────── Desde el TPV, como siempre ───────────────
def test_el_camarero_factura_un_cobro_suelto(cliente, camarero, mesa):
    """El hermano fiscal del ticket individual que ya existía."""
    otro = _segundo_telefono(cliente, mesa)
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, otro, AGUA)
    pago = _paga(cliente, mesa["cab"], con_compartido=False)

    r = cliente.post(f"/api/pagos/{pago['pago_id']}/factura", headers=camarero,
                     json={"tipo": "completa", "cliente_nif": "11111111H",
                           "cliente_nombre": "Bruno SL"})
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["total_cent"] == pago["importe_cent"] and f["pago_id"] == pago["pago_id"]
    # El documento que se imprime es el del cobro, no el de la mesa entera.
    assert f["documento"]["lineas"] and f["documento"]["total_cent"] == pago["importe_cent"]


def test_la_factura_de_un_cobro_se_reimprime_con_su_propio_detalle(cliente, camarero, mesa):
    """Reimprimirla no puede sacar las líneas de toda la mesa: sería otro documento."""
    otro = _segundo_telefono(cliente, mesa)
    pid = _pide(cliente, mesa["cab"], HAMBURGUESA)["pedido_id"]
    _pide(cliente, otro, AGUA, 2)
    pago = _paga(cliente, mesa["cab"], con_compartido=False)
    f = cliente.post(f"/api/pagos/{pago['pago_id']}/factura", headers=camarero, json={}).json()

    doc = cliente.get(f"/api/facturas/{f['id']}", headers=camarero).json()["documento"]
    assert doc["total_cent"] == pago["importe_cent"]
    assert sum(l["importe_cent"] for l in doc["lineas"]) == doc["total_cent"]
    total = cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["total_cent"]
    assert doc["total_cent"] < total

    # Y la pantalla del pedido sabe qué facturas hay y con qué número, para poder decirlo.
    dp = cliente.get(f"/api/pedidos/{pid}/documento", headers=camarero).json()
    assert dp["factura"] is None
    assert [x["numero_completo"] for x in dp["facturas_por_cabeza"]] == [doc["numero_completo"]]


def test_la_numeracion_no_se_repite(cliente, camarero, encargado, pedido_enviado):
    """Dos facturas seguidas, dos números distintos en la misma serie."""
    assert cliente.post(f"/api/pedidos/{pedido_enviado}/cobrar", headers=camarero,
                        json={"metodo": "tarjeta"}).status_code == 200
    una = cliente.post(f"/api/pedidos/{pedido_enviado}/factura", headers=camarero, json={})
    assert una.status_code == 201, una.text
    d = una.json()
    listado = cliente.get("/api/facturas", headers=encargado).json()
    numeros = [f["numero"] for f in listado if f["ejercicio"] == d["ejercicio"]]
    assert len(numeros) == len(set(numeros)), "hay dos facturas con el mismo número"
    assert max(numeros) >= d["numero"]


def test_los_cobros_del_dia_no_se_repiten_por_tener_varias_facturas(cliente, camarero, mesa):
    """Un pedido con factura por cabeza sale UNA vez en la lista de cobros, no una por factura."""
    otro = _segundo_telefono(cliente, mesa)
    _pide(cliente, mesa["cab"], HAMBURGUESA)
    _pide(cliente, otro, AGUA)
    uno = _paga(cliente, mesa["cab"], con_compartido=False)
    dos = _paga(cliente, otro, con_compartido=True)
    for pago in (uno, dos):
        assert cliente.post(f"/api/pagos/{pago['pago_id']}/factura", headers=camarero,
                            json={}).status_code == 201

    cobros = cliente.get("/api/cobros", headers=camarero).json()
    ids = [c["id"] for c in cobros]
    assert len(ids) == len(set(ids)), "la lista de cobros duplica el pedido"
    mio = next(c for c in cobros if c["mesa"] == mesa["mesa"]["nombre"])
    assert mio["facturas_por_cabeza"] == 2 and mio["factura_id"] is None
