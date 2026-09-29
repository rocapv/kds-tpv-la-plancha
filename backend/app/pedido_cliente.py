"""El filtro que decide si la comanda del cliente entra sola en cocina o espera a un camarero.

La idea es que lo normal pase sin molestar a nadie, y que lo raro se pare **con el motivo
escrito**. Nada de rechazar en silencio: el cliente ve que su pedido está esperando confirmación
y por qué, y la sala ve exactamente qué regla saltó para decidir en dos segundos.

Todas las reglas se comprueban aquí, en el servidor. Lo que diga el teléfono no cuenta: ni el
precio, ni la cantidad, ni la mesa.
"""
from .db import q, q1


def _ajustes() -> dict:
    return {f["clave"]: f["valor"] for f in q("SELECT clave, valor FROM ajustes")}


def config() -> dict:
    a = _ajustes()

    def entero(clave, por_defecto):
        try:
            return int(a.get(clave, por_defecto))
        except (TypeError, ValueError):
            return por_defecto

    def lista(clave):
        return {t.strip() for t in str(a.get(clave, "")).split(",") if t.strip()}

    return {
        "directo": str(a.get("cliente_pedido_directo", "si")).strip().lower()
                   in ("si", "sí", "1", "true"),
        "max_unidades": entero("cliente_max_unidades_linea", 10),
        "max_lineas": entero("cliente_max_lineas_pedido", 25),
        "max_importe": entero("cliente_max_importe_cent", 15000),
        "max_por_hora": entero("cliente_max_pedidos_hora", 12),
        "confirmar_categorias": lista("cliente_confirmar_categorias"),
    }


def revisar(lineas: list[dict], mesa_id: int | None, cfg: dict) -> str | None:
    """Devuelve el motivo por el que esta comanda tiene que esperar, o None si puede pasar.

    `lineas` son las que ya ha validado el servidor: cada una con su producto, cantidad, precio
    y categoría. Se devuelve **el primer motivo**, no una lista: quien lo lee necesita saber qué
    hacer, no un informe.
    """
    if not cfg["directo"]:
        return "El local tiene puesto que todas las comandas pasen por un camarero"

    if len(lineas) > cfg["max_lineas"]:
        return f"{len(lineas)} líneas en un pedido; el máximo son {cfg['max_lineas']}"

    for l in lineas:
        if l["cantidad"] > cfg["max_unidades"]:
            return (f"{l['cantidad']} unidades de {l['nombre']}; "
                    f"el máximo por línea son {cfg['max_unidades']}")

    total = sum(l["cantidad"] * l["precio_cent"] for l in lineas)
    if total > cfg["max_importe"]:
        return (f"{total / 100:.2f} € en un pedido; por encima de "
                f"{cfg['max_importe'] / 100:.2f} € lo confirma un camarero")

    if cfg["confirmar_categorias"]:
        for l in lineas:
            if str(l["categoria_id"]) in cfg["confirmar_categorias"]:
                return f"{l['nombre']} es de una categoría que siempre confirma un camarero"

    if mesa_id:
        recientes = q1("""SELECT COUNT(*) n FROM solicitudes
                          WHERE mesa_id=%s AND creada_en >= NOW() - INTERVAL 1 HOUR""",
                       (mesa_id,))["n"]
        if recientes >= cfg["max_por_hora"]:
            return (f"Esta mesa lleva {recientes} pedidos en una hora; "
                    f"el máximo son {cfg['max_por_hora']}")

    return None


def lineas_validadas(pedidas: list) -> list[dict]:
    """Comprueba producto a producto y devuelve lo que de verdad se va a pedir.

    El precio lo pone el servidor **siempre**, con el valor de este momento: si el teléfono
    lleva la carta de hace una hora y el precio ha cambiado, manda el de ahora.
    """
    from fastapi import HTTPException

    salida = []
    for l in pedidas:
        pr = q1("""SELECT id, nombre, precio_cent, estacion, disponible, categoria_id
                   FROM productos WHERE id=%s AND activo""", (l.producto_id,))
        if not pr:
            raise HTTPException(404, "Ese producto ya no está en la carta")
        if not pr["disponible"]:
            raise HTTPException(409, f"{pr['nombre']} se ha agotado")
        salida.append({**pr, "cantidad": l.cantidad, "notas": l.notas})
    return salida
