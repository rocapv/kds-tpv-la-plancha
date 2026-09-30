"""La cuenta de la mesa cuando cada uno paga lo suyo.

La regla que manda sobre todas las demás: **la suma de lo cobrado es la cuenta, ni un céntimo
más ni uno menos**. De ahí salen las dos decisiones que parecen detalles y no lo son:

  · **Lo compartido** (la botella de agua, el pan: líneas sin dueño) se reparte entre los
    comensales que **aún no han pagado**. Si uno se adelanta, paga su parte de lo que había en la
    mesa en ese momento; el que paga el último se lleva lo que quede.
  · **Al último se le cobra el pendiente exacto**, no una división. Repartir en tercios 10,00 €
    da 3,33 tres veces y falta un céntimo: cobrando al último lo que falta, la caja cuadra
    siempre y nadie tiene que discutir por un céntimo.

Los pagos parciales y el enganche de líneas ya existían para dividir cuentas desde el TPV; esto
solo decide **cuánto le toca a cada uno** y deja la marca de quién pagó qué.
"""
from fastapi import HTTPException

from .db import q, q1


def _lineas(pedido_id: int) -> list[dict]:
    return q("""SELECT l.id, l.comensal_id, l.cantidad, l.precio_cent, l.pago_id, l.estado,
                       pr.nombre AS producto
                FROM lineas_pedido l JOIN productos pr ON pr.id=l.producto_id
                WHERE l.pedido_id=%s AND l.estado<>'anulada' ORDER BY l.id""", (pedido_id,))


def _importe(lineas: list[dict]) -> int:
    return sum(l["cantidad"] * l["precio_cent"] for l in lineas)


def resumen(pedido_id: int) -> dict:
    """Cómo queda la cuenta ahora mismo: quién debe qué y cuánto falta."""
    # `total_cent` vive en la vista de totales, no en `pedidos`: el total es la suma de sus
    # líneas, y una columna repetida en la tabla sería un número que se puede quedar viejo.
    p = q1("""SELECT p.id, p.estado, v.total_cent, m.nombre AS mesa
              FROM v_totales_pedido v JOIN pedidos p ON p.id=v.pedido_id
              LEFT JOIN mesas m ON m.id=p.mesa_id WHERE p.id=%s""", (pedido_id,))
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    lineas = _lineas(pedido_id)
    gente = q("SELECT id, sitio, nombre FROM comensales WHERE pedido_id=%s ORDER BY sitio",
              (pedido_id,))
    pagado = q1("SELECT COALESCE(SUM(importe_cent),0) n FROM pagos WHERE pedido_id=%s",
                (pedido_id,))["n"]
    total = _importe(lineas)
    compartidas = [l for l in lineas if l["comensal_id"] is None]
    # Lo compartido que queda por pagar NO son «las líneas compartidas sin marcar»: quien paga su
    # parte se lleva un trozo de la botella, y la botella no se puede partir en la base de datos.
    # Se calcula por diferencia: lo que falta de la cuenta menos lo que falta de platos con dueño.
    # Sin esto, el segundo en pagar cargaba con la parte del primero (0,66 / 1,00 / 0,34 en vez de
    # 0,66 / 0,67 / 0,67): la caja cuadraba, pero el reparto era injusto.
    pendiente_propio = _importe([l for l in lineas if l["comensal_id"] and not l["pago_id"]])
    compartido_pendiente = max(0, (total - pagado) - pendiente_propio)

    # Quién ha pagado ya: lo dice su pago, no sus líneas. En una mesa donde todo es compartido
    # (tres personas y una botella) nadie tiene líneas propias, y sin esta marca el reparto se
    # hacía siempre entre tres y la caja acababa a dos céntimos del total.
    pagos_suyos = {f["comensal_id"]: f["n"] for f in
                   q("""SELECT comensal_id, COUNT(*) n FROM pagos
                        WHERE pedido_id=%s AND comensal_id IS NOT NULL
                        GROUP BY comensal_id""", (pedido_id,))}
    cuentas = []
    for c in gente:
        suyas = [l for l in lineas if l["comensal_id"] == c["id"]]
        pendientes = [l for l in suyas if not l["pago_id"]]
        cuentas.append({
            "comensal_id": c["id"], "sitio": c["sitio"], "nombre": c["nombre"],
            "suyo_cent": _importe(suyas),
            "pendiente_cent": _importe(pendientes),
            "pagado": bool(pagos_suyos.get(c["id"])) or (bool(suyas) and not pendientes),
            "lineas": pendientes,
        })

    # A quién le toca todavía parte de lo compartido: los que siguen debiendo algo, y también
    # los que no pidieron nada propio pero están sentados (alguien que solo picó del centro).
    deben = [c for c in cuentas if not c["pagado"]]
    reparto = len(deben)
    for i, c in enumerate(deben):
        if reparto == 1:
            c["compartido_cent"] = compartido_pendiente          # el último se lleva el resto
        else:
            c["compartido_cent"] = compartido_pendiente // reparto
        c["a_pagar_cent"] = c["pendiente_cent"] + c["compartido_cent"]
    for c in cuentas:
        c.setdefault("compartido_cent", 0)
        c.setdefault("a_pagar_cent", 0)

    return {"pedido_id": pedido_id, "mesa": p["mesa"], "estado": p["estado"],
            "total_cent": total, "pagado_cent": pagado, "pendiente_cent": total - pagado,
            "compartido_cent": _importe(compartidas),
            "compartido_pendiente_cent": compartido_pendiente,
            "cuentas": cuentas, "sin_repartir": len(deben)}


def cobro_de(pedido_id: int, comensal_id: int, con_compartido: bool = True) -> dict:
    """Qué se le cobra a este comensal si paga ahora: importe y qué líneas se marcan.

    Si es el **último** que queda por pagar, se le cobra lo que falte de la cuenta entera: así lo
    que se ha cobrado suma exactamente el total, sin céntimos sueltos por el reparto.
    """
    r = resumen(pedido_id)
    mio = next((c for c in r["cuentas"] if c["comensal_id"] == comensal_id), None)
    if not mio:
        raise HTTPException(404, "Ese comensal no está en esta mesa")
    if mio["pagado"]:
        raise HTTPException(409, f"{mio['nombre'] or 'Ese comensal'} ya ha pagado lo suyo")

    ultimo = r["sin_repartir"] <= 1
    lineas = [l["id"] for l in mio["lineas"]]
    importe = mio["pendiente_cent"] + (mio["compartido_cent"] if con_compartido else 0)
    if ultimo and con_compartido:
        importe = r["pendiente_cent"]                       # cuadre exacto: lo que falte
        lineas += [l["id"] for l in _lineas(pedido_id)
                   if l["comensal_id"] is None and not l["pago_id"]]
    elif con_compartido and mio["compartido_cent"]:
        # Su parte de lo compartido se cobra, pero las líneas compartidas NO se marcan todavía:
        # siguen abiertas hasta que alguien liquide lo que queda de ellas.
        pass
    if importe <= 0:
        raise HTTPException(409, "No hay nada que cobrarle")
    return {"comensal": mio, "importe_cent": importe, "lineas": lineas, "ultimo": ultimo,
            "concepto": (mio["nombre"] or f"Sitio {mio['sitio']}")[:60]}


def partes_iguales(pedido_id: int, partes: int) -> dict:
    """Dividir a partes iguales lo que queda por pagar.

    No es lo mismo que «cada uno lo suyo»: aquí nadie mira lo que pidió. La última parte se lleva
    los céntimos del redondeo, que es la única manera de que la suma sea exacta.
    """
    if partes < 2 or partes > 30:
        raise HTTPException(422, "Se divide entre 2 y 30 partes")
    r = resumen(pedido_id)
    if r["pendiente_cent"] <= 0:
        raise HTTPException(409, "El pedido ya está pagado")
    parte = r["pendiente_cent"] // partes
    return {"pendiente_cent": r["pendiente_cent"], "partes": partes, "parte_cent": parte,
            "ultima_parte_cent": r["pendiente_cent"] - parte * (partes - 1)}


def documento_de_pago(pago_id: int) -> dict:
    """El ticket de un pago concreto: lo que se llevó esa persona y lo que puso.

    Lleva el aviso de que es parte de la cuenta de la mesa, porque un ticket suelto sin contexto
    parece la cuenta entera y luego no cuadra con lo que se cobró.
    """
    g = q1("""SELECT p.*, pe.mesa_id, pe.cerrado_en, m.nombre AS mesa
              FROM pagos p JOIN pedidos pe ON pe.id=p.pedido_id
              LEFT JOIN mesas m ON m.id=pe.mesa_id WHERE p.id=%s""", (pago_id,))
    if not g:
        raise HTTPException(404, "Ese pago no existe")
    lineas = q("""SELECT l.cantidad, l.precio_cent, pr.nombre AS producto
                  FROM lineas_pedido l JOIN productos pr ON pr.id=l.producto_id
                  WHERE l.pago_id=%s ORDER BY l.id""", (pago_id,))
    hermanos = q1("SELECT COUNT(*) n FROM pagos WHERE pedido_id=%s", (g["pedido_id"],))["n"]
    return {"pago": g, "lineas": lineas, "de_varios": hermanos > 1, "pagos_de_la_mesa": hermanos}
