"""El almacén: sin entrada y salida, el TPV no puede saber cuánto queda.

La regla, tal cual la pidió RocaPV: el sistema no puede decir si hay pollo si nadie apunta que
**entró** pollo del proveedor y que **salió** pollo al venderlo. Aquí se comprueba justo eso, de
punta a punta: entra género, se vende, se acaba, el producto se cae solo de la carta y al
reponer vuelve.
"""
import pytest

from conftest import mesa_libre

ARTICULO = 1          # «Proteína cultivada en bloque», kg — de la semilla
PRODUCTO = 2          # un plato de la carta


@pytest.fixture
def plato_con_receta(cliente, encargado):
    """Un plato que gasta 1 kg del artículo 1 por unidad, y el almacén a cero para él.

    Se deja como estaba al terminar: estas pruebas corren sobre una base efímera, pero la
    receta y el stock son datos que otras pruebas miran.
    """
    antes = cliente.get(f"/api/productos/{PRODUCTO}/receta", headers=encargado).json()
    cliente.put(f"/api/productos/{PRODUCTO}/receta", headers=encargado,
                json={"lineas": [{"inventario_id": ARTICULO, "cantidad": 1}]})
    yield PRODUCTO
    cliente.put(f"/api/productos/{PRODUCTO}/receta", headers=encargado,
                json={"lineas": [{"inventario_id": l["inventario_id"], "cantidad": float(l["cantidad"])}
                                 for l in antes["lineas"]]})


def stock(cliente, encargado, aid=ARTICULO):
    art = next(a for a in cliente.get("/api/almacen", headers=encargado).json()["articulos"]
               if a["id"] == aid)
    return float(art["stock"])


def test_una_entrada_de_proveedor_suma(cliente, encargado):
    antes = stock(cliente, encargado)
    r = cliente.post("/api/almacen/entrada", headers=encargado,
                     json={"proveedor": "Hidrocultivos Vesta", "documento": "ALB-001",
                           "lineas": [{"inventario_id": ARTICULO, "cantidad": 10}]})
    assert r.status_code == 201
    assert stock(cliente, encargado) == antes + 10


def test_vender_descuenta_del_almacen(cliente, camarero, encargado, plato_con_receta):
    """Mandar la comanda a cocina es lo que gasta el género: ahí se elabora el plato."""
    cliente.post("/api/almacen/entrada", headers=encargado,
                 json={"proveedor": "Prueba", "lineas": [{"inventario_id": ARTICULO, "cantidad": 20}]})
    antes = stock(cliente, encargado)

    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "llevar", "cliente": "Almacén"}).json()["id"]
    cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                 json={"producto_id": plato_con_receta, "cantidad": 3})
    # apuntarlo todavía no gasta nada: hasta que no va a cocina, se puede quitar
    assert stock(cliente, encargado) == antes

    cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
    assert stock(cliente, encargado) == antes - 3, "tres unidades tienen que gastar tres kilos"

    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)
    assert stock(cliente, encargado) == antes, "lo anulado vuelve al almacén"


def test_el_saldo_cuadra_con_su_historia(cliente, encargado):
    """El saldo es un número rápido; la verdad es la suma de los movimientos."""
    cliente.post("/api/almacen/entrada", headers=encargado,
                 json={"proveedor": "Cuadre", "lineas": [{"inventario_id": ARTICULO, "cantidad": 7}]})
    d = cliente.get(f"/api/almacen/{ARTICULO}/movimientos", headers=encargado).json()
    assert d["cuadra"], f"saldo {d['saldo']} frente a libro {d['libro']}"
    assert d["movimientos"][0]["motivo"] == "albaran"


def test_sin_genero_el_producto_se_cae_de_la_carta(cliente, camarero, encargado, plato_con_receta):
    """Lo que pedía RocaPV: que el TPV pueda marcar algo como no disponible, y solo."""
    # se deja el artículo justo a cero con un recuento
    cliente.post(f"/api/almacen/{ARTICULO}/ajuste", headers=encargado,
                 json={"cantidad": 0, "motivo": "recuento", "nota": "prueba"})
    carta = cliente.get("/api/catalogo?todo=true", headers=encargado).json()
    plato = next(p for c in carta for p in c["productos"] if p["id"] == plato_con_receta)
    assert not plato["disponible"], "sin género, el plato no se puede pedir"

    # y el TPV lo impide de verdad, no solo lo pinta gris
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "llevar", "cliente": "Agotado"}).json()["id"]
    r = cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                     json={"producto_id": plato_con_receta, "cantidad": 1})
    assert r.status_code == 409

    # llega el proveedor y vuelve a la carta, sin que nadie toque una casilla
    cliente.post("/api/almacen/entrada", headers=encargado,
                 json={"proveedor": "Reposición", "lineas": [{"inventario_id": ARTICULO, "cantidad": 25}]})
    carta = cliente.get("/api/catalogo?todo=true", headers=encargado).json()
    plato = next(p for c in carta for p in c["productos"] if p["id"] == plato_con_receta)
    assert plato["disponible"], "con género, el plato vuelve solo"
    cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)


def test_una_merma_se_apunta_con_su_motivo(cliente, encargado):
    antes = stock(cliente, encargado)
    cliente.post(f"/api/almacen/{ARTICULO}/ajuste", headers=encargado,
                 json={"cantidad": -2, "motivo": "merma", "nota": "Se cayó una caja"})
    assert stock(cliente, encargado) == antes - 2
    m = cliente.get(f"/api/almacen/{ARTICULO}/movimientos", headers=encargado).json()["movimientos"][0]
    assert m["motivo"] == "merma" and m["nota"] == "Se cayó una caja"


def test_el_almacen_es_del_encargado(cliente, camarero):
    """Un camarero no da de alta género ni corrige el stock."""
    assert cliente.get("/api/almacen", headers=camarero).status_code == 403
    assert cliente.post("/api/almacen/entrada", headers=camarero,
                        json={"proveedor": "X", "lineas": [{"inventario_id": ARTICULO, "cantidad": 1}]}
                        ).status_code == 403


def test_un_producto_sin_receta_no_lo_toca_el_almacen(cliente, encargado):
    """De un café con leche nadie quiere llevar el gramaje: sin receta, el almacén no opina."""
    sin_receta = cliente.get("/api/productos/15/receta", headers=encargado).json()
    assert sin_receta["posibles"] is None or sin_receta["lineas"] == []
