"""El almacén: entradas, salidas y una carta que se ajusta sola a lo que queda.

La regla del sitio, dicha por RocaPV: el TPV no puede saber cuánto pollo hay si nadie apunta
que **entró** pollo del proveedor y que **salió** pollo al venderlo. Así que aquí todo movimiento
queda escrito en `movimientos_inventario` (positivo entra, negativo sale) y el saldo de
`inventario.stock` se mueve **en la misma transacción**: el saldo es el número rápido que mira
el TPV, y el libro es el que explica cómo se llegó a él. Se puede comprobar que cuadran
(`saldo_cuadra`), y si no cuadran manda el libro.

Cuándo se descuenta: **al mandar la comanda a cocina**, que es cuando el plato se elabora de
verdad. No al apuntarlo (aún se puede quitar) ni al cobrarlo (para entonces ya se ha comido).
Si esa comanda se anula, lo consumido se devuelve.
"""
from decimal import Decimal

from .db import conn, q, q1


def ajuste_si(clave: str, por_defecto: bool = True) -> bool:
    fila = q1("SELECT valor FROM ajustes WHERE clave=%s", (clave,))
    if not fila:
        return por_defecto
    return str(fila["valor"]).strip().lower() in ("si", "sí", "1", "true")


# ─────────────── El libro mayor ───────────────
def apuntar(cur, inventario_id: int, cantidad, motivo: str, empleado_id: int,
            nota: str | None = None, albaran_id: int | None = None) -> None:
    """Un movimiento y su efecto en el saldo, dentro de la MISMA transacción.

    Nunca se toca `inventario.stock` por su cuenta: si el saldo cambiara sin dejar apunte, el
    inventario volvería a ser una foto vieja, que es justo lo que se quería arreglar.
    """
    cur.execute("""INSERT INTO movimientos_inventario
                     (inventario_id, cantidad, motivo, albaran_id, nota, empleado_id)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (inventario_id, cantidad, motivo, albaran_id, nota, empleado_id))
    cur.execute("UPDATE inventario SET stock = stock + %s WHERE id=%s", (cantidad, inventario_id))


def saldo_cuadra(inventario_id: int) -> dict:
    """¿El saldo coincide con la suma de su historia? Lo usa la pantalla y una prueba."""
    f = q1("""SELECT i.stock AS saldo,
                     COALESCE((SELECT SUM(m.cantidad) FROM movimientos_inventario m
                               WHERE m.inventario_id = i.id), 0) AS libro
              FROM inventario i WHERE i.id=%s""", (inventario_id,))
    if not f:
        return {"cuadra": True, "saldo": 0, "libro": 0}
    return {"cuadra": Decimal(f["saldo"]) == Decimal(f["libro"]),
            "saldo": f["saldo"], "libro": f["libro"]}


# ─────────────── Lo que gasta cada plato ───────────────
def receta(producto_id: int) -> list[dict]:
    return q("""SELECT r.inventario_id, r.cantidad, i.nombre, i.unidad, i.stock
                FROM producto_receta r JOIN inventario i ON i.id = r.inventario_id
                WHERE r.producto_id=%s AND i.activo""", (producto_id,))


def unidades_posibles(producto_id: int) -> int | None:
    """Cuántas unidades de ese plato se pueden hacer con lo que queda.

    `None` = sin receta, así que el almacén no opina: hay productos (un café, un refresco de
    máquina) que no se quiere llevar al gramo, y obligar a ponerles receta solo conseguiría que
    alguien apagara el inventario entero.
    """
    filas = receta(producto_id)
    if not filas:
        return None
    posibles = []
    for f in filas:
        cantidad = Decimal(f["cantidad"])
        if cantidad <= 0:
            continue
        posibles.append(int(Decimal(f["stock"]) // cantidad))
    return min(posibles) if posibles else None


# ─────────────── Vender descuenta, anular devuelve ───────────────
def _lineas_con_receta(cur, pid: int, estados: tuple[str, ...]) -> list[tuple[int, int]]:
    marcas = ",".join(["%s"] * len(estados))
    cur.execute(f"""SELECT producto_id, cantidad FROM lineas_pedido
                    WHERE pedido_id=%s AND estado IN ({marcas})""", (pid, *estados))
    return [(f["producto_id"], f["cantidad"]) for f in cur.fetchall()]


def consumir_pedido(pid: int, empleado_id: int) -> int:
    """Descuenta del almacén lo que gastan las líneas que acaban de entrar en cocina."""
    if not ajuste_si("inventario_descontar"):
        return 0
    tocados = set()
    with conn() as c, c.cursor() as cur:
        for producto_id, unidades in _lineas_con_receta(cur, pid, ("enviada",)):
            for ing in receta(producto_id):
                gasto = Decimal(ing["cantidad"]) * unidades
                if gasto <= 0:
                    continue
                apuntar(cur, ing["inventario_id"], -gasto, "consumo", empleado_id,
                        f"Pedido #{pid}")
                tocados.add(ing["inventario_id"])
    revisar_carta()
    return len(tocados)


def devolver_pedido(pid: int, empleado_id: int) -> int:
    """Lo contrario: una comanda anulada devuelve al almacén lo que había reservado.

    Solo se devuelve lo que se llegó a descontar (líneas que pasaron por cocina). Una línea que
    se quitó antes de enviarla nunca gastó nada, así que devolverla inventaría género.
    """
    if not ajuste_si("inventario_descontar"):
        return 0
    tocados = set()
    with conn() as c, c.cursor() as cur:
        cur.execute("""SELECT producto_id, cantidad FROM lineas_pedido
                       WHERE pedido_id=%s AND enviada_en IS NOT NULL""", (pid,))
        for f in cur.fetchall():
            for ing in receta(f["producto_id"]):
                vuelve = Decimal(ing["cantidad"]) * f["cantidad"]
                if vuelve <= 0:
                    continue
                apuntar(cur, ing["inventario_id"], vuelve, "ajuste", empleado_id,
                        f"Anulado el pedido #{pid}")
                tocados.add(ing["inventario_id"])
    revisar_carta()
    return len(tocados)


# ─────────────── La carta se ajusta a lo que queda ───────────────
def revisar_carta() -> dict:
    """Marca agotado lo que ya no se puede hacer, y lo devuelve a la carta cuando llega género.

    Se toca solo `disponible`, nunca `activo`: agotado es «hoy no hay», no «esto ya no existe».
    Y no se toca ningún producto sin receta: de esos el almacén no sabe nada.
    """
    if not ajuste_si("inventario_agota_carta"):
        return {"agotados": 0, "repuestos": 0}
    agotados = repuestos = 0
    for p in q("""SELECT DISTINCT p.id, p.disponible FROM productos p
                  JOIN producto_receta r ON r.producto_id = p.id WHERE p.activo"""):
        posibles = unidades_posibles(p["id"])
        if posibles is None:
            continue
        hay = posibles >= 1
        if hay and not p["disponible"]:
            q("UPDATE productos SET disponible=1 WHERE id=%s", (p["id"],))
            repuestos += 1
        elif not hay and p["disponible"]:
            q("UPDATE productos SET disponible=0 WHERE id=%s", (p["id"],))
            agotados += 1
    return {"agotados": agotados, "repuestos": repuestos}


# ─────────────── Lo que enseña la pantalla ───────────────
def listado() -> list[dict]:
    """Los artículos con su saldo, su mínimo y para cuántos platos da."""
    filas = q("""SELECT i.*, (SELECT COUNT(*) FROM producto_receta r WHERE r.inventario_id=i.id) AS platos
                 FROM inventario i WHERE i.activo ORDER BY i.nombre""")
    for f in filas:
        f["bajo"] = Decimal(f["stock"]) <= Decimal(f["minimo"]) and Decimal(f["minimo"]) > 0
        f["sin"] = Decimal(f["stock"]) <= 0
    return filas
