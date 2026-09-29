"""El grupo sentado en la mesa: quién ocupa cada sitio y de quién es cada plato.

La rejilla tiene el tamaño de la mesa: una de seis se pinta 2×3, una de cuatro 2×2, una de dos
2×1. No es decoración — que los sitios sean los de la mesa de verdad es lo que permite decir «el
de la esquina» y que todos entiendan lo mismo.

Nada de esto es obligatorio. Una línea sin comensal es «de la mesa», y una mesa sin comensales se
comporta como siempre: se pide, se cobra entera y se acabó.
"""
from fastapi import HTTPException

from .db import conn, q, q1


def mesa_del_pedido(pedido_id: int) -> dict:
    p = q1("""SELECT p.id, p.estado, p.mesa_id, p.comensales AS cuantos,
                     m.nombre AS mesa, m.plazas
              FROM pedidos p LEFT JOIN mesas m ON m.id=p.mesa_id WHERE p.id=%s""", (pedido_id,))
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    return p


def sitios(pedido_id: int) -> int:
    """Cuántos sitios tiene la rejilla.

    Las plazas de la mesa mandan, pero si el camarero ha apuntado más comensales que plazas
    (una silla extra, un niño en brazos) la rejilla crece con ellos: lo que no puede pasar es
    que alguien no tenga dónde sentarse en la pantalla.
    """
    p = mesa_del_pedido(pedido_id)
    return max(p["plazas"] or 0, p["cuantos"] or 0, 1)


def listar(pedido_id: int) -> dict:
    """La rejilla entera: cada sitio con quién está, lo que ha pedido y cuánto lleva gastado."""
    p = mesa_del_pedido(pedido_id)
    total_sitios = sitios(pedido_id)
    gente = q("SELECT * FROM comensales WHERE pedido_id=%s ORDER BY sitio", (pedido_id,))
    lineas = q("""SELECT l.id, l.comensal_id, l.cantidad, l.precio_cent, l.estado, l.pago_id,
                         pr.nombre AS producto
                  FROM lineas_pedido l JOIN productos pr ON pr.id=l.producto_id
                  WHERE l.pedido_id=%s AND l.estado<>'anulada'
                  ORDER BY l.id""", (pedido_id,))

    por_comensal: dict[int | None, list] = {}
    for l in lineas:
        por_comensal.setdefault(l["comensal_id"], []).append(l)

    def bloque(comensal):
        suyas = por_comensal.get(comensal["id"] if comensal else None, [])
        return {
            "id": comensal["id"] if comensal else None,
            "sitio": comensal["sitio"] if comensal else None,
            "nombre": comensal["nombre"] if comensal else None,
            "con_movil": bool(comensal and comensal["dispositivo"]),
            "lineas": suyas,
            "total_cent": sum(l["cantidad"] * l["precio_cent"] for l in suyas),
            "pagado": bool(suyas) and all(l["pago_id"] for l in suyas),
        }

    ocupados = {c["sitio"]: c for c in gente}
    rejilla = []
    for sitio in range(1, total_sitios + 1):
        c = ocupados.get(sitio)
        rejilla.append(bloque(c) if c else {"id": None, "sitio": sitio, "nombre": None,
                                            "con_movil": False, "lineas": [], "total_cent": 0,
                                            "pagado": False, "libre": True})
    # Los que se sentaron en un sitio que ya no existe (la mesa encogió) no se pierden: van al final.
    for c in gente:
        if c["sitio"] > total_sitios:
            rejilla.append(bloque(c))

    compartido = bloque(None)
    return {"pedido_id": pedido_id, "mesa": p["mesa"], "plazas": total_sitios,
            "columnas": 2 if total_sitios > 2 else 1,
            "rejilla": rejilla, "de_la_mesa": compartido,
            "total_cent": sum(l["cantidad"] * l["precio_cent"] for l in lineas)}


def sentar(pedido_id: int, sitio: int | None, nombre: str | None,
           dispositivo: str | None = None) -> dict:
    """Pone a alguien en un sitio. Sin sitio, en el primero que quede libre."""
    mesa_del_pedido(pedido_id)
    total = sitios(pedido_id)
    ocupados = {c["sitio"] for c in q("SELECT sitio FROM comensales WHERE pedido_id=%s",
                                      (pedido_id,))}
    if sitio is None:
        sitio = next((s for s in range(1, total + 1) if s not in ocupados), len(ocupados) + 1)
    elif sitio in ocupados:
        raise HTTPException(409, f"El sitio {sitio} ya está ocupado")
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO comensales (pedido_id, sitio, nombre, dispositivo)
                       VALUES (%s,%s,%s,%s)""",
                    (pedido_id, sitio, (nombre or "").strip()[:40] or None, dispositivo))
        cid = cur.lastrowid
    return q1("SELECT * FROM comensales WHERE id=%s", (cid,))


def de_dispositivo(pedido_id: int, token: str) -> dict | None:
    return q1("SELECT * FROM comensales WHERE pedido_id=%s AND dispositivo=%s",
              (pedido_id, token))


def asegurar_para_dispositivo(pedido_id: int, token: str, alias: str | None) -> dict:
    """El móvil que pide desde la mesa tiene su sitio: lo que pide es suyo.

    Así el reparto sale solo, sin que nadie tenga que decir de quién era cada plato.
    """
    return de_dispositivo(pedido_id, token) or sentar(pedido_id, None, alias, token)


def renombrar(comensal_id: int, nombre: str | None) -> dict:
    c = q1("SELECT * FROM comensales WHERE id=%s", (comensal_id,))
    if not c:
        raise HTTPException(404, "Ese comensal no está en la mesa")
    q("UPDATE comensales SET nombre=%s WHERE id=%s",
      ((nombre or "").strip()[:40] or None, comensal_id))
    return q1("SELECT * FROM comensales WHERE id=%s", (comensal_id,))


def levantar(comensal_id: int) -> None:
    """Se va de la mesa. Lo que pidió **no se borra**: pasa a ser de la mesa, porque alguien se
    lo ha comido y hay que cobrarlo."""
    c = q1("SELECT id FROM comensales WHERE id=%s", (comensal_id,))
    if not c:
        raise HTTPException(404, "Ese comensal no está en la mesa")
    q("UPDATE lineas_pedido SET comensal_id=NULL WHERE comensal_id=%s", (comensal_id,))
    q("DELETE FROM comensales WHERE id=%s", (comensal_id,))


def mover_linea(linea_id: int, comensal_id: int | None) -> dict:
    """«Eso es mío». Lo más usado de toda la pantalla."""
    l = q1("SELECT id, pedido_id, pago_id FROM lineas_pedido WHERE id=%s", (linea_id,))
    if not l:
        raise HTTPException(404, "Línea no encontrada")
    if l["pago_id"]:
        raise HTTPException(409, "Esa línea ya está pagada: no se puede cambiar de cuenta")
    if comensal_id is not None:
        c = q1("SELECT id FROM comensales WHERE id=%s AND pedido_id=%s",
               (comensal_id, l["pedido_id"]))
        if not c:
            raise HTTPException(404, "Ese comensal no está en esta mesa")
    q("UPDATE lineas_pedido SET comensal_id=%s WHERE id=%s", (comensal_id, linea_id))
    return {"linea_id": linea_id, "comensal_id": comensal_id}
