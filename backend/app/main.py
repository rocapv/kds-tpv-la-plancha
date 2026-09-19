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
from fastapi.responses import RedirectResponse
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
    p["pagos"] = q("SELECT * FROM pagos WHERE pedido_id=%s", (pid,))
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
def catalogo():
    cats = q("SELECT * FROM categorias ORDER BY orden")
    prods = q("SELECT * FROM productos WHERE activo ORDER BY categoria_id, id")
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
    pr = q1("SELECT precio_cent, estacion FROM productos WHERE id=%s AND activo", (d.producto_id,))
    if not pr:
        raise HTTPException(404, "Producto no disponible")
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


# ─────────────── Frontend estático ───────────────
@app.get("/")
def raiz():
    return RedirectResponse("/index.html")


app.mount("/", StaticFiles(directory=FRONT), name="front")
