"""KDS + TPV · API REST + WebSocket.

TPV (sala)  ──POST──►  API  ──WS evento──►  KDS (cocina, por estación)
                        │
                     MariaDB
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import conn, q, q1

app = FastAPI(title="KDS + TPV · La Plancha", version="1.0")
FRONT = Path(__file__).resolve().parents[2] / "frontend"
ESTACIONES = ("plancha", "freidora", "frios", "barra")


# ─────────────── WebSocket: difusión de eventos a pantallas ───────────────
class Hub:
    def __init__(self):
        self.clientes: set[WebSocket] = set()

    async def entrar(self, ws: WebSocket):
        await ws.accept()
        self.clientes.add(ws)

    def salir(self, ws: WebSocket):
        self.clientes.discard(ws)

    async def emitir(self, tipo: str, **datos):
        msg = json.dumps({"tipo": tipo, **datos}, default=str)
        for ws in list(self.clientes):
            try:
                await ws.send_text(msg)
            except Exception:
                self.salir(ws)


hub = Hub()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await hub.entrar(ws)
    try:
        while True:
            await ws.receive_text()  # ping del cliente; no esperamos órdenes por aquí
    except WebSocketDisconnect:
        hub.salir(ws)


# ─────────────── Modelos de entrada ───────────────
class Login(BaseModel):
    pin: str = Field(min_length=4, max_length=4)


class NuevoPedido(BaseModel):
    empleado_id: int
    tipo: str = "sala"
    mesa_id: int | None = None
    cliente: str | None = None


class NuevaLinea(BaseModel):
    producto_id: int
    cantidad: int = Field(1, ge=1, le=50)
    notas: str | None = Field(None, max_length=120)


class CambioEstado(BaseModel):
    estado: str


class Cobro(BaseModel):
    metodo: str
    entregado_cent: int | None = None


class NuevoEmpleado(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    rol: str
    pin: str = Field(pattern=r"^\d{4}$")
    activo: bool = True


class CambioEmpleado(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=60)
    rol: str | None = None
    pin: str | None = Field(None, pattern=r"^\d{4}$")
    activo: bool | None = None


class DatosFactura(BaseModel):
    tipo: str = "simplificada"
    cliente_nif: str | None = Field(None, max_length=20)
    cliente_nombre: str | None = Field(None, max_length=80)
    cliente_direccion: str | None = Field(None, max_length=120)


class NuevoProducto(BaseModel):
    categoria_id: int
    nombre: str = Field(min_length=2, max_length=60)
    precio_cent: int = Field(ge=0, le=100000)
    estacion: str
    alergenos: str | None = Field(None, max_length=120)
    orden: int = Field(0, ge=0, le=127)


class CambioProducto(BaseModel):
    categoria_id: int | None = None
    nombre: str | None = Field(None, min_length=2, max_length=60)
    precio_cent: int | None = Field(None, ge=0, le=100000)
    estacion: str | None = None
    alergenos: str | None = Field(None, max_length=120)
    orden: int | None = Field(None, ge=0, le=127)
    activo: bool | None = None
    disponible: bool | None = None


class NuevaCategoria(BaseModel):
    nombre: str = Field(min_length=2, max_length=40)
    color: str = Field("#888888", pattern=r"^#[0-9a-fA-F]{6}$")
    orden: int = Field(0, ge=0, le=127)


class CambioCategoria(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    orden: int | None = Field(None, ge=0, le=127)
    activa: bool | None = None


class NuevoPago(BaseModel):
    metodo: str
    lineas: list[int] | None = None       # pago de unas líneas concretas
    importe_cent: int | None = None       # o un importe suelto (división en partes)
    entregado_cent: int | None = None
    concepto: str | None = Field(None, max_length=60)


class Ajuste(BaseModel):
    valor: str = Field(max_length=200)


# ─────────────── Utilidades ───────────────
def pedido_completo(pid: int):
    p = q1("""SELECT p.*, m.nombre AS mesa, e.nombre AS camarero
              FROM pedidos p LEFT JOIN mesas m ON m.id=p.mesa_id
              JOIN empleados e ON e.id=p.empleado_id WHERE p.id=%s""", (pid,))
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    p["lineas"] = q("""SELECT l.*, pr.nombre AS producto FROM lineas_pedido l
                       JOIN productos pr ON pr.id=l.producto_id
                       WHERE l.pedido_id=%s ORDER BY l.id""", (pid,))
    p["total_cent"] = sum(l["cantidad"] * l["precio_cent"] for l in p["lineas"] if l["estado"] != "anulada")
    p["pagos"] = q("SELECT * FROM pagos WHERE pedido_id=%s ORDER BY id", (pid,))
    p["pagado_cent"] = sum(g["importe_cent"] for g in p["pagos"])
    p["pendiente_cent"] = p["total_cent"] - p["pagado_cent"]
    return p


def exigir_abierto(pid: int):
    p = q1("SELECT estado FROM pedidos WHERE id=%s", (pid,))
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    if p["estado"] != "abierto":
        raise HTTPException(409, f"El pedido está {p['estado']}")


# ─────────────── Catálogo y sala ───────────────
@app.get("/api/salud")
def salud():
    q1("SELECT 1 AS ok")
    return {"ok": True, "hora": datetime.now()}


@app.post("/api/login")
def login(d: Login):
    e = q1("SELECT id, nombre, rol FROM empleados WHERE pin=%s AND activo", (d.pin,))
    if not e:
        raise HTTPException(401, "PIN incorrecto")
    return e


@app.get("/api/catalogo")
def catalogo(todo: bool = False):
    """La carta. Con todo=true incluye bajas y agotados (lo usa la app de carta)."""
    cats = q("SELECT * FROM categorias" + ("" if todo else " WHERE activa") + " ORDER BY orden, id")
    prods = q("SELECT * FROM productos" + ("" if todo else " WHERE activo") + " ORDER BY categoria_id, orden, id")
    for c in cats:
        c["productos"] = [p for p in prods if p["categoria_id"] == c["id"]]
    return cats


@app.get("/api/mesas")
def mesas():
    return q("""SELECT m.*, p.id AS pedido_id, p.abierto_en, v.total_cent
                FROM mesas m
                LEFT JOIN pedidos p ON p.mesa_id=m.id AND p.estado='abierto'
                LEFT JOIN v_totales_pedido v ON v.pedido_id=p.id
                ORDER BY m.zona, m.id""")


# ─────────────── Pedidos (TPV) ───────────────
@app.get("/api/pedidos")
def pedidos_abiertos():
    return q("""SELECT p.id, p.tipo, p.cliente, p.abierto_en, m.nombre AS mesa, v.total_cent
                FROM pedidos p LEFT JOIN mesas m ON m.id=p.mesa_id
                JOIN v_totales_pedido v ON v.pedido_id=p.id
                WHERE p.estado='abierto' ORDER BY p.id""")


@app.post("/api/pedidos")
async def crear_pedido(d: NuevoPedido):
    if d.tipo == "sala":
        if not d.mesa_id:
            raise HTTPException(422, "Falta la mesa")
        ya = q1("SELECT id FROM pedidos WHERE mesa_id=%s AND estado='abierto'", (d.mesa_id,))
        if ya:
            return pedido_completo(ya["id"])
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO pedidos (tipo, mesa_id, empleado_id, cliente) VALUES (%s,%s,%s,%s)",
                    (d.tipo, d.mesa_id if d.tipo == "sala" else None, d.empleado_id, d.cliente))
        pid = cur.lastrowid
    await hub.emitir("mesas")
    return pedido_completo(pid)


@app.get("/api/pedidos/{pid}")
def ver_pedido(pid: int):
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/lineas")
async def anadir_linea(pid: int, d: NuevaLinea):
    exigir_abierto(pid)
    pr = q1("SELECT nombre, precio_cent, estacion, disponible FROM productos WHERE id=%s AND activo",
            (d.producto_id,))
    if not pr:
        raise HTTPException(404, "Producto no disponible")
    if not pr["disponible"]:
        raise HTTPException(409, f"{pr['nombre']} está agotado")
    q("""INSERT INTO lineas_pedido (pedido_id, producto_id, cantidad, precio_cent, notas, estacion)
         VALUES (%s,%s,%s,%s,%s,%s)""",
      (pid, d.producto_id, d.cantidad, pr["precio_cent"], d.notas or None, pr["estacion"]))
    await hub.emitir("mesas")
    return pedido_completo(pid)


@app.delete("/api/pedidos/{pid}/lineas/{lid}")
async def quitar_linea(pid: int, lid: int):
    exigir_abierto(pid)
    l = q1("SELECT estado FROM lineas_pedido WHERE id=%s AND pedido_id=%s", (lid, pid))
    if not l:
        raise HTTPException(404, "Línea no encontrada")
    if l["estado"] == "pendiente":
        q("DELETE FROM lineas_pedido WHERE id=%s", (lid,))
    else:  # ya está en cocina: se anula y cocina lo ve
        q("UPDATE lineas_pedido SET estado='anulada' WHERE id=%s", (lid,))
        await hub.emitir("kds")
    await hub.emitir("mesas")
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/enviar")
async def enviar_a_cocina(pid: int):
    exigir_abierto(pid)
    with conn() as c, c.cursor() as cur:
        n = cur.execute("""UPDATE lineas_pedido SET estado='enviada', enviada_en=NOW()
                           WHERE pedido_id=%s AND estado='pendiente'""", (pid,))
    if n:
        await hub.emitir("kds", pedido_id=pid, nuevas=n)
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/cobrar")
async def cobrar(pid: int, d: Cobro):
    exigir_abierto(pid)
    if d.metodo not in ("efectivo", "tarjeta", "bizum"):
        raise HTTPException(422, "Método de pago no válido")
    p = pedido_completo(pid)
    total = p["total_cent"]
    if total == 0:
        raise HTTPException(409, "El pedido está vacío")
    if any(l["estado"] == "pendiente" for l in p["lineas"]):
        raise HTTPException(409, "Hay líneas sin enviar a cocina")
    if p["pagado_cent"]:
        raise HTTPException(409, "El pedido tiene pagos parciales: usa /pagos")
    cambio = None
    if d.metodo == "efectivo":
        if d.entregado_cent is None or d.entregado_cent < total:
            raise HTTPException(422, "Importe entregado insuficiente")
        cambio = d.entregado_cent - total
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO pagos (pedido_id, metodo, importe_cent, entregado_cent, cambio_cent)
                       VALUES (%s,%s,%s,%s,%s)""", (pid, d.metodo, total, d.entregado_cent, cambio))
        cur.execute("UPDATE pedidos SET estado='cobrado', cerrado_en=NOW() WHERE id=%s", (pid,))
    await hub.emitir("mesas")
    await hub.emitir("kds")
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/anular")
async def anular(pid: int):
    exigir_abierto(pid)
    q("UPDATE lineas_pedido SET estado='anulada' WHERE pedido_id=%s AND estado NOT IN ('servida')", (pid,))
    q("UPDATE pedidos SET estado='anulado', cerrado_en=NOW() WHERE id=%s", (pid,))
    await hub.emitir("mesas")
    await hub.emitir("kds")
    return {"ok": True}


# ─────────────── KDS (cocina) ───────────────
@app.get("/api/kds")
def kds(estacion: str | None = None):
    """Comandas activas agrupadas por pedido. Sin estación = vista de pase (todas)."""
    if estacion and estacion not in ESTACIONES:
        raise HTTPException(422, "Estación desconocida")
    filtro = "AND l.estacion=%s" if estacion else ""
    args = (estacion,) if estacion else ()
    filas = q(f"""SELECT l.id, l.pedido_id, l.cantidad, l.notas, l.estacion, l.estado,
                         l.enviada_en, l.lista_en, pr.nombre AS producto,
                         p.tipo, p.cliente, m.nombre AS mesa, e.nombre AS camarero
                  FROM lineas_pedido l
                  JOIN pedidos p   ON p.id=l.pedido_id
                  JOIN productos pr ON pr.id=l.producto_id
                  JOIN empleados e ON e.id=p.empleado_id
                  LEFT JOIN mesas m ON m.id=p.mesa_id
                  WHERE l.estado IN ('enviada','preparando','lista') {filtro}
                    AND p.estado <> 'anulado'
                  ORDER BY l.enviada_en, l.pedido_id, l.id""", args)
    comandas = {}
    for f in filas:
        c = comandas.setdefault(f["pedido_id"], {
            "pedido_id": f["pedido_id"], "mesa": f["mesa"], "tipo": f["tipo"],
            "cliente": f["cliente"], "camarero": f["camarero"],
            "desde": f["enviada_en"], "lineas": []})
        c["desde"] = min(c["desde"], f["enviada_en"])
        c["lineas"].append(f)
    return {"ahora": datetime.now(), "comandas": list(comandas.values())}


SIGUIENTE = {"enviada": "preparando", "preparando": "lista", "lista": "servida"}


@app.patch("/api/lineas/{lid}")
async def cambiar_estado_linea(lid: int, d: CambioEstado):
    l = q1("SELECT estado, pedido_id FROM lineas_pedido WHERE id=%s", (lid,))
    if not l:
        raise HTTPException(404, "Línea no encontrada")
    nuevo = SIGUIENTE.get(l["estado"]) if d.estado == "siguiente" else d.estado
    if nuevo not in ("enviada", "preparando", "lista", "servida"):
        raise HTTPException(409, f"No se puede pasar de {l['estado']} a {d.estado}")
    q("UPDATE lineas_pedido SET estado=%s, lista_en=IF(%s='lista', NOW(), lista_en) WHERE id=%s",
      (nuevo, nuevo, lid))
    await hub.emitir("kds", pedido_id=l["pedido_id"])
    if nuevo == "lista":
        await hub.emitir("listo", pedido_id=l["pedido_id"], linea_id=lid)
    return {"id": lid, "estado": nuevo}


@app.post("/api/kds/pedido/{pid}/avanzar")
async def avanzar_pedido(pid: int, estacion: str | None = None):
    """Botón 'bump': avanza todas las líneas del pedido (de esa estación) un paso."""
    filtro = "AND estacion=%s" if estacion else ""
    args = (pid, estacion) if estacion else (pid,)
    lineas = q(f"""SELECT id, estado FROM lineas_pedido WHERE pedido_id=%s
                   AND estado IN ('enviada','preparando','lista') {filtro}""", args)
    if not lineas:
        raise HTTPException(404, "Nada que avanzar")
    minimo = min(lineas, key=lambda x: list(SIGUIENTE).index(x["estado"]))["estado"]
    nuevo = SIGUIENTE[minimo]
    ids = [x["id"] for x in lineas if x["estado"] == minimo]
    marcas = ",".join(["%s"] * len(ids))
    q(f"UPDATE lineas_pedido SET estado=%s, lista_en=IF(%s='lista', NOW(), lista_en) WHERE id IN ({marcas})",
      (nuevo, nuevo, *ids))
    await hub.emitir("kds", pedido_id=pid)
    if nuevo == "lista":
        await hub.emitir("listo", pedido_id=pid)
    return {"pedido_id": pid, "estado": nuevo, "lineas": len(ids)}


# ─────────────── Informes (encargado) ───────────────
@app.get("/api/informe")
def informe(fecha: str | None = None):
    dia = fecha or datetime.now().strftime("%Y-%m-%d")
    resumen = q1("""SELECT COUNT(*) AS tickets, COALESCE(SUM(importe_cent),0) AS total_cent
                    FROM pagos WHERE DATE(pagado_en)=%s""", (dia,))
    por_metodo = q("""SELECT metodo, COUNT(*) AS tickets, SUM(importe_cent) AS total_cent
                      FROM pagos WHERE DATE(pagado_en)=%s GROUP BY metodo""", (dia,))
    top = q("""SELECT pr.nombre, SUM(l.cantidad) AS unidades, SUM(l.cantidad*l.precio_cent) AS total_cent
               FROM lineas_pedido l JOIN productos pr ON pr.id=l.producto_id
               JOIN pedidos p ON p.id=l.pedido_id
               WHERE p.estado='cobrado' AND DATE(p.cerrado_en)=%s AND l.estado<>'anulada'
               GROUP BY pr.id ORDER BY unidades DESC LIMIT 10""", (dia,))
    por_hora = q("""SELECT HOUR(pagado_en) AS hora, SUM(importe_cent) AS total_cent
                    FROM pagos WHERE DATE(pagado_en)=%s GROUP BY hora ORDER BY hora""", (dia,))
    cocina = q("""SELECT estacion, COUNT(*) AS lineas,
                         ROUND(AVG(TIMESTAMPDIFF(SECOND, enviada_en, lista_en))) AS seg_medio
                  FROM lineas_pedido WHERE lista_en IS NOT NULL AND DATE(lista_en)=%s
                  GROUP BY estacion""", (dia,))
    # IVA incluido en precio (10 % hostelería): base = total / 1,10
    total = int(resumen["total_cent"])
    base = round(total / 1.10)
    return {"fecha": dia, "tickets": resumen["tickets"], "total_cent": total,
            "base_cent": base, "iva_cent": total - base,
            "ticket_medio_cent": round(total / resumen["tickets"]) if resumen["tickets"] else 0,
            "por_metodo": por_metodo, "top": top, "por_hora": por_hora, "cocina": cocina}


# ─────────────── Carta (app de carta) ───────────────
@app.post("/api/categorias", status_code=201)
async def crear_categoria(d: NuevaCategoria):
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO categorias (nombre, color, orden) VALUES (%s,%s,%s)",
                    (d.nombre.strip(), d.color, d.orden))
        cid = cur.lastrowid
    await hub.emitir("carta")
    return q1("SELECT * FROM categorias WHERE id=%s", (cid,))


@app.patch("/api/categorias/{cid}")
async def editar_categoria(cid: int, d: CambioCategoria):
    if not q1("SELECT id FROM categorias WHERE id=%s", (cid,)):
        raise HTTPException(404, "Categoría no encontrada")
    campos = {k: v for k, v in d.model_dump().items() if v is not None}
    if campos:
        sets = ", ".join(f"{k}=%s" for k in campos)
        q(f"UPDATE categorias SET {sets} WHERE id=%s", (*campos.values(), cid))
    await hub.emitir("carta")
    return q1("SELECT * FROM categorias WHERE id=%s", (cid,))


@app.post("/api/productos", status_code=201)
async def crear_producto(d: NuevoProducto):
    if d.estacion not in ESTACIONES:
        raise HTTPException(422, "Estación desconocida")
    if not q1("SELECT id FROM categorias WHERE id=%s", (d.categoria_id,)):
        raise HTTPException(404, "Categoría no encontrada")
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO productos (categoria_id, nombre, precio_cent, estacion, alergenos, orden)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (d.categoria_id, d.nombre.strip(), d.precio_cent, d.estacion, d.alergenos, d.orden))
        pid = cur.lastrowid
    await hub.emitir("carta")
    return q1("SELECT * FROM productos WHERE id=%s", (pid,))


@app.patch("/api/productos/{prid}")
async def editar_producto(prid: int, d: CambioProducto):
    if not q1("SELECT id FROM productos WHERE id=%s", (prid,)):
        raise HTTPException(404, "Producto no encontrado")
    if d.estacion and d.estacion not in ESTACIONES:
        raise HTTPException(422, "Estación desconocida")
    campos = {k: v for k, v in d.model_dump().items() if v is not None}
    if campos:
        sets = ", ".join(f"{k}=%s" for k in campos)
        q(f"UPDATE productos SET {sets} WHERE id=%s", (*campos.values(), prid))
    await hub.emitir("carta")
    return q1("SELECT * FROM productos WHERE id=%s", (prid,))


@app.delete("/api/productos/{prid}")
async def quitar_producto(prid: int):
    """Baja lógica: los pedidos antiguos deben seguir enseñando qué se vendió."""
    if not q1("SELECT id FROM productos WHERE id=%s", (prid,)):
        raise HTTPException(404, "Producto no encontrado")
    q("UPDATE productos SET activo=0 WHERE id=%s", (prid,))
    await hub.emitir("carta")
    return {"ok": True}


# ─────────────── Pagos: dividir cuenta y pago mixto ───────────────
@app.post("/api/pedidos/{pid}/pagos", status_code=201)
async def anadir_pago(pid: int, d: NuevoPago):
    """Un pedido admite varios pagos: por líneas, por partes iguales o a importe libre.

    El pedido se cierra solo cuando lo pagado alcanza el total.
    """
    exigir_abierto(pid)
    if d.metodo not in ("efectivo", "tarjeta", "bizum"):
        raise HTTPException(422, "Método de pago no válido")
    p = pedido_completo(pid)
    if any(l["estado"] == "pendiente" for l in p["lineas"]):
        raise HTTPException(409, "Hay líneas sin enviar a cocina")
    if p["pendiente_cent"] <= 0:
        raise HTTPException(409, "El pedido ya está pagado")

    lineas = []
    if d.lineas:
        por_id = {l["id"]: l for l in p["lineas"]}
        for lid in d.lineas:
            l = por_id.get(lid)
            if not l:
                raise HTTPException(404, f"La línea {lid} no es de este pedido")
            if l["estado"] == "anulada":
                raise HTTPException(409, "Hay líneas anuladas en la selección")
            if l["pago_id"]:
                raise HTTPException(409, f"La línea {lid} ya estaba pagada")
            lineas.append(l)
        importe = sum(l["cantidad"] * l["precio_cent"] for l in lineas)
    elif d.importe_cent is not None:
        importe = d.importe_cent
    else:
        importe = p["pendiente_cent"]
    if importe <= 0:
        raise HTTPException(422, "El importe debe ser mayor que cero")
    if importe > p["pendiente_cent"]:
        raise HTTPException(422, "El importe supera lo que queda por pagar")

    cambio = None
    if d.metodo == "efectivo" and d.entregado_cent is not None:
        if d.entregado_cent < importe:
            raise HTTPException(422, "Importe entregado insuficiente")
        cambio = d.entregado_cent - importe

    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO pagos (pedido_id, metodo, concepto, importe_cent, entregado_cent, cambio_cent)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (pid, d.metodo, d.concepto, importe, d.entregado_cent, cambio))
        pago_id = cur.lastrowid
        if lineas:
            marcas = ",".join(["%s"] * len(lineas))
            cur.execute(f"UPDATE lineas_pedido SET pago_id=%s WHERE id IN ({marcas})",
                        (pago_id, *[l["id"] for l in lineas]))
        cur.execute("SELECT COALESCE(SUM(importe_cent),0) AS pagado FROM pagos WHERE pedido_id=%s", (pid,))
        if cur.fetchone()["pagado"] >= p["total_cent"]:
            cur.execute("UPDATE pedidos SET estado='cobrado', cerrado_en=NOW() WHERE id=%s", (pid,))
    await hub.emitir("mesas")
    return pedido_completo(pid)


@app.delete("/api/pedidos/{pid}/pagos/{pago_id}")
async def anular_pago(pid: int, pago_id: int):
    """Solo se deshace mientras el pedido siga abierto (error de caja reciente)."""
    exigir_abierto(pid)
    if not q1("SELECT id FROM pagos WHERE id=%s AND pedido_id=%s", (pago_id, pid)):
        raise HTTPException(404, "Pago no encontrado")
    q("UPDATE lineas_pedido SET pago_id=NULL WHERE pago_id=%s", (pago_id,))
    q("DELETE FROM pagos WHERE id=%s", (pago_id,))
    await hub.emitir("mesas")
    return pedido_completo(pid)


# ─────────────── Empleados (app de usuarios) ───────────────
ROLES = ("camarero", "cocina", "encargado")


@app.get("/api/empleados")
def listar_empleados(todos: bool = False):
    return q("SELECT id, nombre, rol, pin, activo FROM empleados" +
             ("" if todos else " WHERE activo") + " ORDER BY rol, nombre")


@app.post("/api/empleados", status_code=201)
def crear_empleado(d: NuevoEmpleado):
    if d.rol not in ROLES:
        raise HTTPException(422, "Rol no válido")
    if q1("SELECT id FROM empleados WHERE pin=%s", (d.pin,)):
        raise HTTPException(409, "Ese PIN ya está en uso")
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO empleados (nombre, rol, pin, activo) VALUES (%s,%s,%s,%s)",
                    (d.nombre.strip(), d.rol, d.pin, d.activo))
        eid = cur.lastrowid
    return q1("SELECT id, nombre, rol, pin, activo FROM empleados WHERE id=%s", (eid,))


@app.patch("/api/empleados/{eid}")
def editar_empleado(eid: int, d: CambioEmpleado):
    if not q1("SELECT id FROM empleados WHERE id=%s", (eid,)):
        raise HTTPException(404, "Empleado no encontrado")
    if d.rol and d.rol not in ROLES:
        raise HTTPException(422, "Rol no válido")
    if d.pin and q1("SELECT id FROM empleados WHERE pin=%s AND id<>%s", (d.pin, eid)):
        raise HTTPException(409, "Ese PIN ya está en uso")
    campos = {k: v for k, v in d.model_dump().items() if v is not None}
    if campos:
        sets = ", ".join(f"{k}=%s" for k in campos)
        q(f"UPDATE empleados SET {sets} WHERE id=%s", (*campos.values(), eid))
    return q1("SELECT id, nombre, rol, pin, activo FROM empleados WHERE id=%s", (eid,))


@app.delete("/api/empleados/{eid}")
def baja_empleado(eid: int):
    """No se borra: se da de baja. Sus pedidos históricos deben seguir teniendo autor."""
    if not q1("SELECT id FROM empleados WHERE id=%s", (eid,)):
        raise HTTPException(404, "Empleado no encontrado")
    if q1("SELECT COUNT(*) n FROM empleados WHERE activo AND rol='encargado' AND id<>%s", (eid,))["n"] == 0        and q1("SELECT rol FROM empleados WHERE id=%s", (eid,))["rol"] == "encargado":
        raise HTTPException(409, "Debe quedar al menos un encargado activo")
    q("UPDATE empleados SET activo=0 WHERE id=%s", (eid,))
    return {"ok": True}


# ─────────────── Ajustes del local ───────────────
def ajustes_dict():
    return {r["clave"]: r["valor"] for r in q("SELECT clave, valor FROM ajustes")}


@app.get("/api/ajustes")
def ver_ajustes():
    return ajustes_dict()


@app.put("/api/ajustes/{clave}")
def poner_ajuste(clave: str, d: Ajuste):
    if not q1("SELECT clave FROM ajustes WHERE clave=%s", (clave,)):
        raise HTTPException(404, "Ajuste desconocido")
    q("UPDATE ajustes SET valor=%s WHERE clave=%s", (d.valor, clave))
    return {clave: d.valor}


# ─────────────── Facturación (todo en pantalla, sin impresora) ───────────────
def factura_completa(fid: int):
    f = q1("SELECT * FROM facturas WHERE id=%s", (fid,))
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    f["numero_completo"] = f"{f['serie']}{f['ejercicio']}/{f['numero']:05d}"
    f["local"] = ajustes_dict()
    f["pedido"] = pedido_completo(f["pedido_id"])
    return f


@app.post("/api/pedidos/{pid}/factura", status_code=201)
def emitir_factura(pid: int, d: DatosFactura):
    p = pedido_completo(pid)
    if p["estado"] != "cobrado":
        raise HTTPException(409, "Solo se factura un pedido cobrado")
    ya = q1("SELECT id FROM facturas WHERE pedido_id=%s", (pid,))
    if ya:
        return factura_completa(ya["id"])          # una factura por pedido: idempotente
    if d.tipo == "completa" and not (d.cliente_nif and d.cliente_nombre):
        raise HTTPException(422, "La factura completa necesita NIF y nombre del cliente")
    iva_pct = int(ajustes_dict().get("iva_pct", 10))
    total = p["total_cent"]
    base = round(total / (1 + iva_pct / 100))
    ejercicio = datetime.now().year
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(numero), 0) + 1 AS n FROM facturas WHERE serie='A' AND ejercicio=%s FOR UPDATE",
                    (ejercicio,))
        numero = cur.fetchone()["n"]
        cur.execute("""INSERT INTO facturas (serie, ejercicio, numero, pedido_id, tipo,
                         cliente_nif, cliente_nombre, cliente_direccion, base_cent, iva_cent, total_cent)
                       VALUES ('A',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (ejercicio, numero, pid, d.tipo, d.cliente_nif, d.cliente_nombre,
                     d.cliente_direccion, base, total - base, total))
        fid = cur.lastrowid
    return factura_completa(fid)


@app.get("/api/cobros")
def cobros(fecha: str | None = None):
    """Pedidos cobrados de un día, con su factura si ya se emitió."""
    dia = fecha or datetime.now().strftime("%Y-%m-%d")
    return q("""SELECT p.id, p.tipo, p.cliente, p.cerrado_en, m.nombre AS mesa, e.nombre AS camarero,
                       v.total_cent, f.id AS factura_id,
                       CONCAT(f.serie, f.ejercicio, '/', LPAD(f.numero, 5, '0')) AS numero_completo
                FROM pedidos p
                JOIN v_totales_pedido v ON v.pedido_id=p.id
                JOIN empleados e ON e.id=p.empleado_id
                LEFT JOIN mesas m ON m.id=p.mesa_id
                LEFT JOIN facturas f ON f.pedido_id=p.id
                WHERE p.estado='cobrado' AND DATE(p.cerrado_en)=%s
                ORDER BY p.cerrado_en DESC""", (dia,))


@app.get("/api/facturas")
def listar_facturas(fecha: str | None = None, buscar: str | None = None):
    donde, args = [], []
    if fecha:
        donde.append("DATE(f.emitida_en)=%s"); args.append(fecha)
    if buscar:
        donde.append("(f.cliente_nombre LIKE %s OR f.cliente_nif LIKE %s OR f.numero=%s)")
        args += [f"%{buscar}%", f"%{buscar}%", buscar if buscar.isdigit() else 0]
    sql = """SELECT f.*, CONCAT(f.serie, f.ejercicio, '/', LPAD(f.numero, 5, '0')) AS numero_completo,
                    m.nombre AS mesa, e.nombre AS camarero
             FROM facturas f JOIN pedidos p ON p.id=f.pedido_id
             LEFT JOIN mesas m ON m.id=p.mesa_id JOIN empleados e ON e.id=p.empleado_id"""
    if donde:
        sql += " WHERE " + " AND ".join(donde)
    return q(sql + " ORDER BY f.id DESC LIMIT 200", args)


@app.get("/api/facturas/{fid}")
def ver_factura(fid: int):
    return factura_completa(fid)


@app.get("/api/pedidos/{pid}/documento")
def documento_pedido(pid: int):
    """Datos que necesita la pantalla para pintar el ticket o la factura del pedido."""
    p = pedido_completo(pid)
    f = q1("SELECT id FROM facturas WHERE pedido_id=%s", (pid,))
    iva_pct = int(ajustes_dict().get("iva_pct", 10))
    base = round(p["total_cent"] / (1 + iva_pct / 100))
    return {"pedido": p, "local": ajustes_dict(), "iva_pct": iva_pct,
            "base_cent": base, "iva_cent": p["total_cent"] - base,
            "factura": factura_completa(f["id"]) if f else None}


# ─────────────── Frontend estático ───────────────
@app.middleware("http")
async def sin_cache(request, call_next):
    """El navegador debe revalidar siempre: en clase se edita el front y se recarga."""
    resp = await call_next(request)
    if not request.url.path.startswith("/api"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
    return resp


def version_estaticos() -> str:
    """Sello de version = fecha del fichero mas reciente de css/ y js/.

    Las paginas piden los recursos como /css/estilo.css?v=<sello>: al cambiar un fichero
    cambia la URL y el navegador no puede servir una copia vieja de su cache.
    """
    ficheros = list((FRONT / "css").glob("*.css")) + list((FRONT / "js").glob("*.js"))
    return str(int(max(f.stat().st_mtime for f in ficheros))) if ficheros else "0"


@app.get("/")
def raiz():
    return RedirectResponse("/index.html")


@app.get("/{pagina}.html", response_class=HTMLResponse)
def pagina_html(pagina: str):
    f = (FRONT / f"{pagina}.html").resolve()
    if not f.is_file() or FRONT.resolve() not in f.parents:
        raise HTTPException(404, "Página no encontrada")
    return f.read_text(encoding="utf-8").replace("__V__", version_estaticos())


app.mount("/", StaticFiles(directory=FRONT), name="front")
