"""La factura: quién la pide, de qué parte de la cuenta, y hasta cuándo se emite sola.

Hasta aquí la factura era cosa del TPV: el camarero pulsaba y salía. Lo que se añade es que la
pida **el cliente desde su teléfono**, y eso obliga a escribir tres reglas que antes vivían en la
cabeza de quien estaba en la caja.

**De qué parte.** Una mesa de cuatro que paga a escote genera cuatro cobros. La factura de Ana no
es la de la mesa: es lo que puso Ana. Por eso `facturas.pago_id` —con `0` cuando la factura cubre
la cuenta entera— y por eso la regla que no se puede romper: *o una por cabeza, o una de todos*.
Las dos cosas a la vez serían cobrar dos veces lo mismo sobre el papel.

**Hasta cuándo sola.** Que la app emita facturas de días cerrados descuadra el arqueo de aquel día,
así que mientras la caja del día siga abierta la factura sale sin que intervenga nadie, y después
no. Pero «después ya no se puede» es falso: el Reglamento de facturación (RD 1619/2012) obliga a
expedirla cuando el cliente la pide, y permite hacer una factura completa a partir de una
simplificada ya emitida. Así que después **sí se puede, la emite el encargado**, y el documento
lleva las dos fechas: la de expedición y la de la operación. La app, en vez de decir que es
imposible, dice a qué teléfono o correo hay que pedirla.

**Qué ve el cliente.** `publica()` devuelve el documento sin nada de dentro: ni camarero, ni
estación de cocina, ni el resto de la mesa. Y con el detalle cuadrado, porque en una factura la
suma de las líneas tiene que ser el total; cuando alguien paga su parte de lo compartido, esa parte
aparece como una línea con su nombre y no como un céntimo que falta.
"""
from datetime import datetime

from fastapi import HTTPException

from .db import conn, q, q1

CUENTA_ENTERA = 0          # `pago_id` de la factura que cubre todo el pedido


# ─────────────── Lecturas ───────────────
def _ajuste(clave: str, por_defecto: str = "") -> str:
    fila = q1("SELECT valor FROM ajustes WHERE clave=%s", (clave,))
    return str(fila["valor"]) if fila else por_defecto


def iva_pct() -> int:
    try:
        return int(_ajuste("iva_pct", "10"))
    except ValueError:
        return 10


def datos_del_local() -> dict:
    """Lo del local que va impreso, y solo eso.

    `ajustes` tiene dentro topes de pedido y minutos de aviso; nada de eso pinta en una factura ni
    tiene por qué salir a internet.
    """
    return {c: _ajuste(f"local_{c}") for c in ("nombre", "nif", "direccion", "telefono", "email")}


def numero_completo(f: dict) -> str:
    return f"{f['serie']}{f['ejercicio']}/{f['numero']:05d}"


def fila(fid: int) -> dict:
    f = q1("SELECT * FROM facturas WHERE id=%s", (fid,))
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    f["numero_completo"] = numero_completo(f)
    f["fuera_de_fecha"] = fuera_de_fecha(f)
    return f


def fuera_de_fecha(f: dict) -> bool:
    """¿Se expidió un día distinto del de la operación?

    Cuando es así hay que decirlo en el documento; es lo que distingue una factura emitida en el
    momento de una emitida tres semanas después a petición del cliente.
    """
    if not f.get("operacion_en") or not f.get("emitida_en"):
        return False
    return f["operacion_en"].date() != f["emitida_en"].date()


def de_pedido(pedido_id: int) -> dict | None:
    """La factura de la cuenta entera, si la hay."""
    f = q1("SELECT id FROM facturas WHERE pedido_id=%s AND pago_id=%s",
           (pedido_id, CUENTA_ENTERA))
    return fila(f["id"]) if f else None


def de_pago(pago_id: int) -> dict | None:
    f = q1("SELECT id FROM facturas WHERE pago_id=%s", (pago_id,))
    return fila(f["id"]) if f else None


def del_pedido_por_cabezas(pedido_id: int) -> list[dict]:
    """Las facturas de cobros sueltos de este pedido.

    Lleva el número montado porque quien pregunta esto es una pantalla que tiene que **decir** qué
    facturas hay —«este cobro ya tiene la A2026/00042»— y no solo contarlas.
    """
    return q("""SELECT id, pago_id,
                       CONCAT(serie, ejercicio, '/', LPAD(numero, 5, '0')) AS numero_completo
                FROM facturas WHERE pedido_id=%s AND pago_id<>%s ORDER BY id""",
             (pedido_id, CUENTA_ENTERA))


# ─────────────── El plazo ───────────────
def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def plazo(operacion_en: datetime | None) -> dict:
    """¿Puede la app emitirla sola, o hay que pedírsela al local?

    Abierto solo si la operación es **de hoy** y la caja de hoy no está cerrada. Un día que no es
    hoy ya está contado, aunque nadie haya pulsado el cierre Z: emitir contra él cambiaría un
    arqueo que alguien ya dio por bueno.
    """
    local = datos_del_local()
    como = f"Llama al {local['telefono']}" if local.get("telefono") else "Llama al restaurante"
    if local.get("email"):
        como += f" o escribe a {local['email']}"
    if not operacion_en:
        return {"abierto": False, "motivo": "Esta cuenta todavía no está cobrada", "como_pedirla": como}
    dia = operacion_en.strftime("%Y-%m-%d")
    if dia != _hoy():
        return {"abierto": False, "dia": dia, "como_pedirla": como,
                "motivo": "Esa cuenta es de otro día y su caja ya está cerrada"}
    a = q1("SELECT estado FROM arqueos WHERE fecha=%s", (dia,))
    if a and a["estado"] == "cerrado":
        return {"abierto": False, "dia": dia, "como_pedirla": como,
                "motivo": "La caja del día ya está cerrada"}
    return {"abierto": True, "dia": dia, "motivo": None, "como_pedirla": como}


def app_activa() -> bool:
    return _ajuste("factura_app", "si").strip().lower() in ("si", "sí", "1", "true")


# ─────────────── Emitir ───────────────
def emitir(*, pedido_id: int, total_cent: int, operacion_en: datetime | None,
           pago_id: int = CUENTA_ENTERA, tipo: str = "simplificada",
           nif: str | None = None, nombre: str | None = None, direccion: str | None = None,
           pedida_por: str = "local", cliente_id: int | None = None) -> dict:
    """Emite la factura, o devuelve la que ya había.

    Un ticket solo puede dar lugar a una factura: la segunda petición devuelve la primera, no una
    nueva. Eso ya lo garantizaba la clave única de la tabla, pero hay que devolverla en vez de
    reventar, porque el cliente que pulsa dos veces no está haciendo nada mal.
    """
    if tipo not in ("simplificada", "completa"):
        raise HTTPException(422, "El tipo de factura solo puede ser simplificada o completa")
    ya = q1("SELECT id FROM facturas WHERE pedido_id=%s AND pago_id=%s", (pedido_id, pago_id))
    if ya:
        return fila(ya["id"])

    # O una por cabeza, o una de todos. Nunca las dos: la suma de los justificantes es la cuenta.
    if pago_id == CUENTA_ENTERA:
        por_cabezas = del_pedido_por_cabezas(pedido_id)
        if por_cabezas:
            raise HTTPException(409, f"Esta mesa ya tiene {len(por_cabezas)} factura(s) por cabeza; "
                                     "una de la cuenta entera cobraría dos veces lo mismo")
    elif de_pedido(pedido_id):
        raise HTTPException(409, "Esta mesa ya tiene factura de la cuenta entera; "
                                 "para separarla hay que rectificar aquella")

    if tipo == "completa" and not (nif and nombre):
        raise HTTPException(422, "La factura completa necesita NIF y nombre del cliente")
    if total_cent <= 0:
        raise HTTPException(409, "No se factura un importe de cero")

    pct = iva_pct()
    base = round(total_cent / (1 + pct / 100))
    ejercicio = datetime.now().year          # la numeración va por año de expedición
    with conn() as c, c.cursor() as cur:
        cur.execute("""SELECT COALESCE(MAX(numero), 0) + 1 AS n FROM facturas
                       WHERE serie='A' AND ejercicio=%s FOR UPDATE""", (ejercicio,))
        numero = cur.fetchone()["n"]
        cur.execute("""INSERT INTO facturas (serie, ejercicio, numero, pedido_id, pago_id, tipo,
                         pedida_por, cliente_nif, cliente_nombre, cliente_direccion, cliente_id,
                         base_cent, iva_cent, total_cent, operacion_en)
                       VALUES ('A',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (ejercicio, numero, pedido_id, pago_id, tipo, pedida_por,
                     nif, nombre, direccion, cliente_id,
                     base, total_cent - base, total_cent, operacion_en))
        fid = cur.lastrowid
    return fila(fid)


# ─────────────── El documento que ve el cliente ───────────────
def _lineas_de(f: dict) -> list[dict]:
    """El detalle, cuadrado con el total.

    Cuando alguien paga su parte de lo compartido, las líneas compartidas **no** se marcan con su
    pago (siguen abiertas para los demás), así que las suyas no suman lo que puso. La diferencia se
    escribe con su nombre: en una factura no puede faltar un céntimo sin explicación.
    """
    if f["pago_id"] == CUENTA_ENTERA:
        lineas = q("""SELECT l.cantidad, l.precio_cent, pr.nombre AS producto
                      FROM lineas_pedido l JOIN productos pr ON pr.id=l.producto_id
                      WHERE l.pedido_id=%s AND l.estado<>'anulada' ORDER BY l.id""",
                   (f["pedido_id"],))
    else:
        lineas = q("""SELECT l.cantidad, l.precio_cent, pr.nombre AS producto
                      FROM lineas_pedido l JOIN productos pr ON pr.id=l.producto_id
                      WHERE l.pago_id=%s ORDER BY l.id""", (f["pago_id"],))
    detalle = [{"cantidad": l["cantidad"], "producto": l["producto"],
                "precio_cent": l["precio_cent"],
                "importe_cent": l["cantidad"] * l["precio_cent"]} for l in lineas]
    resto = f["total_cent"] - sum(l["importe_cent"] for l in detalle)
    if resto > 0:
        detalle.append({"cantidad": 1, "producto": "Parte de lo que compartía la mesa",
                        "precio_cent": resto, "importe_cent": resto})
    return detalle


def publica(f: dict | int) -> dict:
    """La factura como la ve el teléfono: el documento y nada de la cocina.

    Ni quién la sirvió, ni en qué plancha se hizo, ni lo que pidieron los demás. Un cliente tiene
    derecho a su factura, no al parte de trabajo del local.
    """
    f = fila(f) if isinstance(f, int) else f
    p = q1("""SELECT p.cerrado_en, m.nombre AS mesa FROM pedidos p
              LEFT JOIN mesas m ON m.id=p.mesa_id WHERE p.id=%s""", (f["pedido_id"],))
    return {"id": f["id"], "numero_completo": f["numero_completo"], "tipo": f["tipo"],
            "emitida_en": f["emitida_en"], "operacion_en": f["operacion_en"],
            "fuera_de_fecha": f["fuera_de_fecha"],
            "alcance": "mesa" if f["pago_id"] == CUENTA_ENTERA else "mio",
            "cliente_nif": f["cliente_nif"], "cliente_nombre": f["cliente_nombre"],
            "cliente_direccion": f["cliente_direccion"],
            "base_cent": f["base_cent"], "iva_cent": f["iva_cent"],
            "total_cent": f["total_cent"], "iva_pct": iva_pct(),
            "local": datos_del_local(), "mesa": p["mesa"] if p else None,
            "lineas": _lineas_de(f)}
