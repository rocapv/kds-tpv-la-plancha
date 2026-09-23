"""KDS + TPV · API REST + WebSocket.

TPV (sala)  ──POST──►  API  ──WS evento──►  KDS (cocina, por estación)
                        │
                     MariaDB
"""
import asyncio
import json
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .red import es_de_la_lan
from .auth import (abrir_sesion, cerrar_sesion, cifrar_clave, exige, exige_nivel,
                   usuario, usuario_de_token)
from .db import conn, q, q1
from .simulacion import simulacion

app = FastAPI(title="KDS + TPV · Cantina Vesta-9", version="1.0")
FRONT = Path(__file__).resolve().parents[2] / "frontend"
def estaciones_validas() -> tuple[str, ...]:
    """Las secciones de cocina viven en la tabla `estaciones` (ver 09_estaciones.sql): abrir un
    broiler nuevo es dar de alta una fila, no tocar el código ni el esquema."""
    return tuple(e["clave"] for e in q("SELECT clave FROM estaciones WHERE activa ORDER BY orden, clave"))


def claves_de_pantalla(estacion: str | None, pantalla: str | None) -> list[str] | None:
    """Qué secciones mira una pantalla de cocina. None = todas (vista de pase).
    `estacion` admite varias separadas por comas; `pantalla` es una fila de `kds_pantallas`."""
    crudo = estacion
    if pantalla:
        fila = q1("SELECT estaciones FROM kds_pantallas WHERE clave=%s AND activa", (pantalla,))
        if not fila:
            raise HTTPException(422, "Esa pantalla de cocina no existe")
        crudo = fila["estaciones"]
    claves = [c.strip() for c in (crudo or "").split(",") if c.strip()]
    if not claves:
        return None
    validas = estaciones_validas()
    desconocidas = [c for c in claves if c not in validas]
    if desconocidas:
        raise HTTPException(422, f"Sección de cocina desconocida: {', '.join(desconocidas)}")
    return claves


def filtro_estaciones(claves: list[str] | None, columna: str = "estacion") -> tuple[str, list]:
    if not claves:
        return "", []
    return f"AND {columna} IN ({','.join(['%s'] * len(claves))})", list(claves)


# ─────────────── WebSocket: difusión de eventos a pantallas ───────────────
class Hub:
    def __init__(self):
        self.clientes: set[WebSocket] = set()
        self.publicos: set[WebSocket] = set()   # pantallas de sala, sin sesión

    async def entrar(self, ws: WebSocket, publico: bool = False):
        await ws.accept()
        (self.publicos if publico else self.clientes).add(ws)

    def salir(self, ws: WebSocket):
        self.clientes.discard(ws)
        self.publicos.discard(ws)

    async def _enviar(self, destinos: set[WebSocket], tipo: str, datos: dict):
        msg = json.dumps({"tipo": tipo, **datos}, default=str)
        for ws in list(destinos):
            try:
                await ws.send_text(msg)
            except Exception:
                self.salir(ws)

    async def emitir(self, tipo: str, **datos):
        await self._enviar(self.clientes, tipo, datos)

    async def emitir_publico(self, tipo: str, **datos):
        """Aviso a las pantallas sin sesión: nunca lleva datos, solo 'vuelve a mirar'."""
        await self._enviar(self.publicos, tipo, datos)


hub = Hub()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str | None = None):
    if not es_de_la_lan(ws.client.host if ws.client else None):
        await ws.close(code=4403)      # 4403: fuera de la red local
        return
    if not usuario_de_token(token):
        await ws.close(code=4401)      # 4401: sesión no válida
        return
    await hub.entrar(ws)
    try:
        while True:
            await ws.receive_text()  # ping del cliente; no esperamos órdenes por aquí
    except WebSocketDisconnect:
        hub.salir(ws)


@app.websocket("/ws/publico")
async def ws_publico(ws: WebSocket):
    """Pantalla de recogida: cuelga en la sala, sin PIN. Solo recibe el aviso 'recogida'."""
    await hub.entrar(ws, publico=True)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.salir(ws)


# ─────────────── Modelos de entrada ───────────────
class Login(BaseModel):
    pin: str | None = Field(None, min_length=4, max_length=4)
    empleado_id: int | None = None          # entrada de gestión: número de empleado…
    contrasena: str | None = Field(None, min_length=6, max_length=100)   # …y contraseña


class NuevoPedido(BaseModel):
    tipo: str = "sala"
    comensales: int | None = Field(None, ge=1, le=30)
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
    apellidos: str | None = Field(None, max_length=80)
    rol: str = "camarero"
    escalafon: str = "base"
    pin: str | None = Field(None, pattern=r"^\d{4}$")      # vacío = lo genera el servidor
    contrasena: str | None = Field(None, min_length=6, max_length=100)
    activo: bool = True


class CambioEmpleado(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=60)
    apellidos: str | None = Field(None, max_length=80)
    rol: str | None = None
    escalafon: str | None = None
    pin: str | None = Field(None, pattern=r"^\d{4}$")
    contrasena: str | None = Field(None, min_length=6, max_length=100)
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
    alergenos: str | None = Field(None, max_length=120)      # texto libre (se recalcula)
    alergenos_claves: list[str] | None = None                # catálogo: lo que manda
    inventario_id: int | None = None
    foto: str | None = Field(None, max_length=200)
    orden: int = Field(0, ge=0, le=127)


class CambioProducto(BaseModel):
    categoria_id: int | None = None
    nombre: str | None = Field(None, min_length=2, max_length=60)
    precio_cent: int | None = Field(None, ge=0, le=100000)
    estacion: str | None = None
    alergenos: str | None = Field(None, max_length=120)
    alergenos_claves: list[str] | None = None
    inventario_id: int | None = None
    foto: str | None = Field(None, max_length=200)
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


class AperturaCaja(BaseModel):
    fondo_cent: int = Field(ge=0)


class MovimientoCaja(BaseModel):
    tipo: str
    importe_cent: int = Field(gt=0)
    motivo: str = Field(max_length=80)


class CierreCaja(BaseModel):
    contado_cent: int = Field(ge=0)
    retirada_cent: int = Field(0, ge=0)
    recuento: dict[str, int] | None = None      # desglose por billetes y monedas
    notas: str | None = Field(None, max_length=200)


class LineaSolicitada(BaseModel):
    producto_id: int
    cantidad: int = Field(1, ge=1, le=20)
    notas: str | None = Field(None, max_length=120)


class Solicitud(BaseModel):
    mesa_id: int | None = None
    cliente: str | None = Field(None, max_length=60)
    nota: str | None = Field(None, max_length=160)
    lineas: list[LineaSolicitada] = Field(min_length=1, max_length=40)


class Ajuste(BaseModel):
    valor: str = Field(max_length=200)


# ─────────────── Utilidades ───────────────
def pedido_completo(pid: int):
    p = q1("""SELECT p.*, m.nombre AS mesa, e.nombre AS camarero
              FROM pedidos p LEFT JOIN mesas m ON m.id=p.mesa_id
              JOIN empleados e ON e.id=p.empleado_id WHERE p.id=%s""", (pid,))
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    p["lineas"] = q("""SELECT l.*, pr.nombre AS producto, pr.alergenos FROM lineas_pedido l
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
def login(d: Login, user_agent: str | None = Header(None)):
    """Único sitio donde viajan el PIN o la contraseña. Devuelve el token de la sesión."""
    if d.contrasena and d.empleado_id:
        return abrir_sesion(None, user_agent, d.empleado_id, d.contrasena)
    if not d.pin:
        raise HTTPException(422, "Hace falta el PIN, o el número de empleado con su contraseña")
    return abrir_sesion(d.pin, user_agent)


@app.post("/api/logout")
def logout(u: dict = Depends(usuario)):
    cerrar_sesion(u["token"])
    return {"ok": True}


@app.get("/api/yo")
def yo(u: dict = Depends(usuario)):
    return {"id": u["id"], "nombre": u["nombre"], "rol": u["rol"], "caduca_en": u["caduca_en"],
            "apellidos": u.get("apellidos"),
            "escalafon": u.get("escalafon"), "escalafon_nombre": u.get("escalafon_nombre"),
            "nivel": u.get("nivel"), "gestion": u.get("gestion"),
            "puesto": u.get("puesto"), "puesto_nombre": u.get("puesto_nombre"),
            "rol_operativo": u.get("rol_operativo"), "gui": u.get("gui"), "guis": u.get("guis", [])}


@app.get("/api/sesiones")
def sesiones_abiertas(u: dict = Depends(exige("encargado"))):
    return q("""SELECT s.token, s.creada_en, s.ultimo_uso, s.caduca_en, s.agente,
                       e.nombre, e.rol
                FROM sesiones s JOIN empleados e ON e.id=s.empleado_id
                WHERE s.caduca_en > NOW() ORDER BY s.ultimo_uso DESC""")


@app.delete("/api/sesiones/{token}")
def cerrar_otra_sesion(token: str, u: dict = Depends(exige("encargado"))):
    cerrar_sesion(token)
    return {"ok": True}


@app.get("/api/catalogo")
def catalogo(todo: bool = False, u: dict = Depends(usuario)):
    """La carta. Con todo=true incluye bajas y agotados (lo usa la app de carta)."""
    cats = q("SELECT * FROM categorias" + ("" if todo else " WHERE activa") + " ORDER BY orden, id")
    prods = q("SELECT * FROM productos" + ("" if todo else " WHERE activo") + " ORDER BY categoria_id, orden, id")
    marcados = {}
    for f in q("SELECT producto_id, alergeno FROM producto_alergenos"):
        marcados.setdefault(f["producto_id"], []).append(f["alergeno"])
    for p in prods:
        p["alergenos_claves"] = marcados.get(p["id"], [])
        p["foto_url"] = p.get("foto") or f"/api/productos/{p['id']}/foto.svg"
    for c in cats:
        c["productos"] = [p for p in prods if p["categoria_id"] == c["id"]]
    return cats


@app.get("/api/mesas")
def mesas(u: dict = Depends(exige("camarero", "encargado"))):
    return q("""SELECT m.*, p.id AS pedido_id, p.abierto_en, v.total_cent
                FROM mesas m
                LEFT JOIN pedidos p ON p.mesa_id=m.id AND p.estado='abierto'
                LEFT JOIN v_totales_pedido v ON v.pedido_id=p.id
                ORDER BY m.zona, m.id""")


# ─────────────── Pedidos (TPV) ───────────────
@app.get("/api/pedidos")
def pedidos_abiertos(u: dict = Depends(exige("camarero", "encargado"))):
    return q("""SELECT p.id, p.tipo, p.cliente, p.abierto_en, m.nombre AS mesa, v.total_cent
                FROM pedidos p LEFT JOIN mesas m ON m.id=p.mesa_id
                JOIN v_totales_pedido v ON v.pedido_id=p.id
                WHERE p.estado='abierto' ORDER BY p.id""")


@app.post("/api/pedidos")
async def crear_pedido(d: NuevoPedido, u: dict = Depends(exige("camarero", "encargado"))):
    if d.tipo == "sala":
        if not d.mesa_id:
            raise HTTPException(422, "Falta la mesa")
        ya = q1("SELECT id FROM pedidos WHERE mesa_id=%s AND estado='abierto'", (d.mesa_id,))
        if ya:
            return pedido_completo(ya["id"])
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO pedidos (tipo, mesa_id, comensales, empleado_id, cliente)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (d.tipo, d.mesa_id if d.tipo == "sala" else None, d.comensales,
                     u["id"], d.cliente))
        pid = cur.lastrowid
    await hub.emitir("mesas")
    return pedido_completo(pid)


@app.get("/api/pedidos/{pid}")
def ver_pedido(pid: int, u: dict = Depends(usuario)):
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/lineas")
async def anadir_linea(pid: int, d: NuevaLinea, u: dict = Depends(exige("camarero", "encargado"))):
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
async def quitar_linea(pid: int, lid: int, u: dict = Depends(exige("camarero", "encargado"))):
    exigir_abierto(pid)
    l = q1("SELECT estado FROM lineas_pedido WHERE id=%s AND pedido_id=%s", (lid, pid))
    if not l:
        raise HTTPException(404, "Línea no encontrada")
    if l["estado"] == "pendiente":
        q("DELETE FROM lineas_pedido WHERE id=%s", (lid,))
    else:  # ya está en cocina: se anula y cocina lo ve
        q("UPDATE lineas_pedido SET estado='anulada' WHERE id=%s", (lid,))
        await hub.emitir("kds")
        await hub.emitir_publico("recogida")
    await hub.emitir("mesas")
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/enviar")
async def enviar_a_cocina(pid: int, u: dict = Depends(exige("camarero", "encargado"))):
    exigir_abierto(pid)
    with conn() as c, c.cursor() as cur:
        n = cur.execute("""UPDATE lineas_pedido SET estado='enviada', enviada_en=NOW()
                           WHERE pedido_id=%s AND estado='pendiente'""", (pid,))
    if n:
        await hub.emitir("kds", pedido_id=pid, nuevas=n)
        await hub.emitir_publico("recogida")
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/cobrar")
async def cobrar(pid: int, d: Cobro, u: dict = Depends(exige("camarero", "encargado"))):
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
    await hub.emitir_publico("recogida")
    return pedido_completo(pid)


@app.post("/api/pedidos/{pid}/anular")
async def anular(pid: int, u: dict = Depends(exige("camarero", "cocina", "encargado"))):
    """Un pedido se puede tirar desde cualquier pantalla: la cocina es la primera que ve que
    esa comanda no tenia que haber entrado."""
    exigir_abierto(pid)
    q("UPDATE lineas_pedido SET estado='anulada' WHERE pedido_id=%s AND estado NOT IN ('servida')", (pid,))
    q("UPDATE pedidos SET estado='anulado', cerrado_en=NOW() WHERE id=%s", (pid,))
    await hub.emitir("mesas")
    await hub.emitir("kds")
    await hub.emitir_publico("recogida")
    return {"ok": True}


# ─────────────── KDS (cocina) ───────────────
# Cuántas comandas se mandan a una pantalla de cocina como mucho. No es una limitación de la
# base de datos, es de la pantalla: nadie cocina mirando doscientas tarjetas, y el navegador de
# una tableta (o de una Raspberry Pi) tiene que repintarlas TODAS en cada aviso. Con la cocina
# atascada, pintarlo todo es justo lo que impide despacharlo. Se mandan las más viejas —que es
# el orden en el que se cocina— y se dice cuántas quedan detrás.
TOPE_KDS = 60
TOPE_RECOGIDA = 24    # números que caben en el tablón de la sala sin encoger la letra


@app.get("/api/kds")
def kds(estacion: str | None = None, pantalla: str | None = None, limite: int = TOPE_KDS,
        u: dict = Depends(usuario)):
    """Comandas activas agrupadas por pedido. Sin secciones = vista de pase (todas).

    Devuelve como mucho `limite` comandas, las más antiguas primero, y en `esperando` cuántas
    se han quedado fuera.
    """
    claves = claves_de_pantalla(estacion, pantalla)
    filtro, args = filtro_estaciones(claves, "l.estacion")
    tope = max(1, min(limite, 500))

    # Primero QUÉ comandas entran (las más viejas), y luego sus líneas: así la consulta gorda
    # no tiene que traerse la cocina entera para tirar casi todo.
    cabeceras = q(f"""SELECT l.pedido_id, MIN(l.enviada_en) AS desde
                      FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id
                      WHERE l.estado IN ('enviada','preparando','lista') {filtro}
                        AND p.estado <> 'anulado'
                      GROUP BY l.pedido_id ORDER BY desde, l.pedido_id
                      LIMIT %s""", (*args, tope + 1))
    esperando = max(0, len(cabeceras) - tope)
    cabeceras = cabeceras[:tope]
    if esperando:
        total = q1(f"""SELECT COUNT(DISTINCT l.pedido_id) AS n
                       FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id
                       WHERE l.estado IN ('enviada','preparando','lista') {filtro}
                         AND p.estado <> 'anulado'""", tuple(args))["n"]
        esperando = total - len(cabeceras)

    comandas = {}
    if cabeceras:
        ids = [c["pedido_id"] for c in cabeceras]
        marcas = ",".join(["%s"] * len(ids))
        filas = q(f"""SELECT l.id, l.pedido_id, l.cantidad, l.notas, l.estacion, l.estado,
                             l.enviada_en, l.lista_en, pr.nombre AS producto, pr.alergenos,
                             p.tipo, p.cliente, m.nombre AS mesa, e.nombre AS camarero
                      FROM lineas_pedido l
                      JOIN pedidos p   ON p.id=l.pedido_id
                      JOIN productos pr ON pr.id=l.producto_id
                      JOIN empleados e ON e.id=p.empleado_id
                      LEFT JOIN mesas m ON m.id=p.mesa_id
                      WHERE l.estado IN ('enviada','preparando','lista') {filtro}
                        AND l.pedido_id IN ({marcas})
                      ORDER BY l.enviada_en, l.pedido_id, l.id""", (*args, *ids))
        for f in filas:
            c = comandas.setdefault(f["pedido_id"], {
                "pedido_id": f["pedido_id"], "mesa": f["mesa"], "tipo": f["tipo"],
                "cliente": f["cliente"], "camarero": f["camarero"],
                "desde": f["enviada_en"], "lineas": []})
            c["desde"] = min(c["desde"], f["enviada_en"])
            c["lineas"].append(f)
    return {"ahora": datetime.now(), "comandas": list(comandas.values()), "esperando": esperando}


SIGUIENTE = {"enviada": "preparando", "preparando": "lista", "lista": "servida"}
# En cocina se toca la pantalla con las manos ocupadas: hay que poder volver atrás.
ANTERIOR = {v: k for k, v in SIGUIENTE.items()}


def _mover_lineas(ids: list[int], nuevo: str) -> None:
    """Cambia el estado y ajusta `lista_en`: al retroceder por debajo de «lista» se borra,
    para que el tiempo de cocina del informe no cuente un plato que volvió al fuego."""
    marcas = ",".join(["%s"] * len(ids))
    q(f"""UPDATE lineas_pedido
          SET estado=%s,
              lista_en = CASE WHEN %s='lista' THEN NOW()
                              WHEN %s IN ('enviada','preparando') THEN NULL
                              ELSE lista_en END
          WHERE id IN ({marcas})""", (nuevo, nuevo, nuevo, *ids))


@app.patch("/api/lineas/{lid}")
async def cambiar_estado_linea(lid: int, d: CambioEstado, u: dict = Depends(exige("cocina", "encargado"))):
    l = q1("""SELECT l.estado, l.pedido_id, p.estado AS estado_pedido
              FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id WHERE l.id=%s""", (lid,))
    if not l:
        raise HTTPException(404, "Línea no encontrada")
    if d.estado == "siguiente":
        nuevo = SIGUIENTE.get(l["estado"])
    elif d.estado == "anterior":
        nuevo = ANTERIOR.get(l["estado"])
        if not nuevo:
            raise HTTPException(409, f"«{l['estado']}» ya es el primer paso: no hay nada que deshacer")
        if l["estado_pedido"] != "abierto":
            raise HTTPException(409, "El pedido ya está cerrado: no se puede deshacer")
    else:
        nuevo = d.estado
    if nuevo not in ("enviada", "preparando", "lista", "servida"):
        raise HTTPException(409, f"No se puede pasar de {l['estado']} a {d.estado}")
    _mover_lineas([lid], nuevo)
    await hub.emitir("kds", pedido_id=l["pedido_id"])
    await hub.emitir_publico("recogida")
    if nuevo == "lista":
        await hub.emitir("listo", pedido_id=l["pedido_id"], linea_id=lid)
    return {"id": lid, "estado": nuevo}


@app.post("/api/kds/pedido/{pid}/retroceder")
async def retroceder_pedido(pid: int, estacion: str | None = None, pantalla: str | None = None,
                            u: dict = Depends(exige("cocina", "encargado"))):
    """Deshace el último «bump» de la comanda: el grupo más adelantado vuelve un paso atrás."""
    p = q1("SELECT estado FROM pedidos WHERE id=%s", (pid,))
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    if p["estado"] != "abierto":
        raise HTTPException(409, "El pedido ya está cerrado: no se puede deshacer")
    claves = claves_de_pantalla(estacion, pantalla)
    filtro, extra = filtro_estaciones(claves)
    args = (pid, *extra)
    lineas = q(f"""SELECT id, estado FROM lineas_pedido WHERE pedido_id=%s
                   AND estado IN ('preparando','lista','servida') {filtro}""", args)
    if not lineas:
        raise HTTPException(409, "No hay nada que deshacer en esta comanda")
    orden = ["enviada", "preparando", "lista", "servida"]
    maximo = max(lineas, key=lambda x: orden.index(x["estado"]))["estado"]
    ids = [x["id"] for x in lineas if x["estado"] == maximo]
    _mover_lineas(ids, ANTERIOR[maximo])
    await hub.emitir("kds", pedido_id=pid)
    await hub.emitir_publico("recogida")
    return {"pedido_id": pid, "estado": ANTERIOR[maximo], "lineas": len(ids), "deshecho": maximo}


@app.post("/api/kds/pedido/{pid}/avanzar")
async def avanzar_pedido(pid: int, estacion: str | None = None, pantalla: str | None = None, u: dict = Depends(exige("cocina", "encargado"))):
    """Botón 'bump': avanza todas las líneas del pedido (de esa estación) un paso."""
    claves = claves_de_pantalla(estacion, pantalla)
    filtro, extra = filtro_estaciones(claves)
    args = (pid, *extra)
    lineas = q(f"""SELECT id, estado FROM lineas_pedido WHERE pedido_id=%s
                   AND estado IN ('enviada','preparando','lista') {filtro}""", args)
    if not lineas:
        raise HTTPException(404, "Nada que avanzar")
    minimo = min(lineas, key=lambda x: list(SIGUIENTE).index(x["estado"]))["estado"]
    nuevo = SIGUIENTE[minimo]
    ids = [x["id"] for x in lineas if x["estado"] == minimo]
    _mover_lineas(ids, nuevo)
    await hub.emitir("kds", pedido_id=pid)
    await hub.emitir_publico("recogida")
    if nuevo == "lista":
        await hub.emitir("listo", pedido_id=pid)
    return {"pedido_id": pid, "estado": nuevo, "lineas": len(ids)}


# ─────────────── Pantalla de recogida (pública, sala) ───────────────
@app.get("/api/recogida")
def recogida():
    """Números de los pedidos «para llevar», sin sesión: cuelga en la sala a la vista.

    No devuelve nombres ni importes; solo el número del pedido y cuánto lleva esperando.
    Un pedido desaparece de la pantalla cuando cocina lo marca «servido» (entregado).
    """
    filas = q("""SELECT l.pedido_id, l.estado, l.enviada_en, l.lista_en
                 FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id
                 WHERE p.tipo='llevar' AND p.estado <> 'anulado'
                   AND l.estado IN ('enviada','preparando','lista')
                 ORDER BY l.pedido_id""")
    # El tablón de la sala se lee de lejos: caben unos cuantos números, no doscientos.
    pedidos = {}
    for f in filas:
        d = pedidos.setdefault(f["pedido_id"], {"numero": f["pedido_id"], "estados": set(),
                                                "desde": f["enviada_en"], "lista_en": f["lista_en"]})
        d["estados"].add(f["estado"])
        d["desde"] = min(d["desde"], f["enviada_en"])
        d["lista_en"] = max(filter(None, (d["lista_en"], f["lista_en"])), default=None)
    listos, preparando = [], []
    for d in pedidos.values():
        destino = listos if d.pop("estados") == {"lista"} else preparando
        destino.append(d)
    listos.sort(key=lambda d: d["lista_en"] or d["desde"], reverse=True)
    preparando.sort(key=lambda d: d["desde"])
    aj = ajustes_dict()
    return {"ahora": datetime.now(), "local": aj.get("local_nombre", "Cantina Vesta-9"),
            "listos": listos[:TOPE_RECOGIDA], "preparando": preparando[:TOPE_RECOGIDA],
            "mas_listos": max(0, len(listos) - TOPE_RECOGIDA),
            "mas_preparando": max(0, len(preparando) - TOPE_RECOGIDA)}


# ─────────────── Informes (encargado) ───────────────
@app.get("/api/informe")
def informe(fecha: str | None = None, u: dict = Depends(exige("encargado"))):
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
async def crear_categoria(d: NuevaCategoria, u: dict = Depends(exige("encargado"))):
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO categorias (nombre, color, orden) VALUES (%s,%s,%s)",
                    (d.nombre.strip(), d.color, d.orden))
        cid = cur.lastrowid
    await hub.emitir("carta")
    return q1("SELECT * FROM categorias WHERE id=%s", (cid,))


@app.patch("/api/categorias/{cid}")
async def editar_categoria(cid: int, d: CambioCategoria, u: dict = Depends(exige("encargado"))):
    if not q1("SELECT id FROM categorias WHERE id=%s", (cid,)):
        raise HTTPException(404, "Categoría no encontrada")
    campos = {k: v for k, v in d.model_dump().items() if v is not None}
    if campos:
        sets = ", ".join(f"{k}=%s" for k in campos)
        q(f"UPDATE categorias SET {sets} WHERE id=%s", (*campos.values(), cid))
    await hub.emitir("carta")
    return q1("SELECT * FROM categorias WHERE id=%s", (cid,))


@app.post("/api/productos", status_code=201)
async def crear_producto(d: NuevoProducto, u: dict = Depends(exige("encargado"))):
    if d.estacion not in estaciones_validas():
        raise HTTPException(422, "Estación desconocida")
    if not q1("SELECT id FROM categorias WHERE id=%s", (d.categoria_id,)):
        raise HTTPException(404, "Categoría no encontrada")
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO productos (categoria_id, nombre, precio_cent, estacion, alergenos, orden)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (d.categoria_id, d.nombre.strip(), d.precio_cent, d.estacion, d.alergenos, d.orden))
        pid = cur.lastrowid
    sincronizar_alergenos(pid, d.alergenos_claves)
    if d.inventario_id or d.foto:
        q("UPDATE productos SET inventario_id=%s, foto=%s WHERE id=%s",
          (d.inventario_id, d.foto, pid))
    await hub.emitir("carta")
    return {**q1("SELECT * FROM productos WHERE id=%s", (pid,)), "alergenos_claves": alergenos_de(pid)}


@app.patch("/api/productos/{prid}")
async def editar_producto(prid: int, d: CambioProducto, u: dict = Depends(exige("encargado"))):
    if not q1("SELECT id FROM productos WHERE id=%s", (prid,)):
        raise HTTPException(404, "Producto no encontrado")
    if d.estacion and d.estacion not in estaciones_validas():
        raise HTTPException(422, "Estación desconocida")
    enviados = d.model_dump(exclude_unset=True)
    claves = enviados.pop("alergenos_claves", None)
    # alergenos es el unico campo que se puede vaciar: un null explicito lo borra.
    campos = {k: v for k, v in enviados.items() if v is not None or k == "alergenos"}
    if campos:
        sets = ", ".join(f"{k}=%s" for k in campos)
        q(f"UPDATE productos SET {sets} WHERE id=%s", (*campos.values(), prid))
    sincronizar_alergenos(prid, claves)
    await hub.emitir("carta")
    return {**q1("SELECT * FROM productos WHERE id=%s", (prid,)),
            "alergenos_claves": alergenos_de(prid)}


@app.delete("/api/productos/{prid}")
async def quitar_producto(prid: int, u: dict = Depends(exige("encargado"))):
    """Baja lógica: los pedidos antiguos deben seguir enseñando qué se vendió."""
    if not q1("SELECT id FROM productos WHERE id=%s", (prid,)):
        raise HTTPException(404, "Producto no encontrado")
    q("UPDATE productos SET activo=0 WHERE id=%s", (prid,))
    await hub.emitir("carta")
    return {"ok": True}


# ─────────────── Pagos: dividir cuenta y pago mixto ───────────────
@app.post("/api/pedidos/{pid}/pagos", status_code=201)
async def anadir_pago(pid: int, d: NuevoPago, u: dict = Depends(exige("camarero", "encargado"))):
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
async def anular_pago(pid: int, pago_id: int, u: dict = Depends(exige("camarero", "encargado"))):
    """Solo se deshace mientras el pedido siga abierto (error de caja reciente)."""
    exigir_abierto(pid)
    if not q1("SELECT id FROM pagos WHERE id=%s AND pedido_id=%s", (pago_id, pid)):
        raise HTTPException(404, "Pago no encontrado")
    q("UPDATE lineas_pedido SET pago_id=NULL WHERE pago_id=%s", (pago_id,))
    q("DELETE FROM pagos WHERE id=%s", (pago_id,))
    await hub.emitir("mesas")
    return pedido_completo(pid)


# ─────────────── Empleados, escalafones y contraseñas ───────────────
ROLES = ("camarero", "cocina", "encargado")

CAMPOS_EMPLEADO = """e.id, e.nombre, e.apellidos, e.rol, e.escalafon, e.pin, e.activo, e.alta_en,
                     e.puesto, (e.contrasena IS NOT NULL) AS tiene_contrasena,
                     es.nombre AS escalafon_nombre, es.nivel, es.plus_pct, es.gestion"""

# Para el botón de «invéntame un nombre». Cantina de una estación minera: mezcla de todo.
NOMBRES_PILA = ["Ada", "Iker", "Nerea", "Hugo", "Yuki", "Omar", "Lucía", "Bram", "Noa", "Teo",
                "Amaia", "Rashid", "Sonia", "Dmitri", "Carme", "Iván", "Leire", "Nico"]
APELLIDOS = ["Vega", "Ortiz", "Kowalski", "Serra", "Ibáñez", "Nakamura", "Duarte", "Okonkwo",
             "Pardo", "Lindqvist", "Salinas", "Ferreiro", "Bauer", "Mendoza", "Roca"]


def empleado(eid: int) -> dict | None:
    return q1(f"""SELECT {CAMPOS_EMPLEADO} FROM empleados e
                  LEFT JOIN escalafones es ON es.clave = e.escalafon WHERE e.id=%s""", (eid,))


def pin_libre() -> str:
    usados = {f["pin"] for f in q("SELECT pin FROM empleados")}
    for _ in range(500):
        p = f"{secrets.randbelow(10000):04d}"
        if p not in usados:
            return p
    raise HTTPException(409, "No quedan PIN de cuatro cifras libres")


def contrasena_legible() -> str:
    """Contraseña generada que se pueda dictar por teléfono: dos palabras y dos cifras."""
    return (f"{secrets.choice(APELLIDOS).lower()}-{secrets.choice(NOMBRES_PILA).lower()}"
            f"-{secrets.randbelow(100):02d}")


@app.get("/api/escalafones")
def listar_escalafones(u: dict = Depends(usuario)):
    return q("SELECT * FROM escalafones ORDER BY nivel")


@app.get("/api/empleados/sugerencia")
def sugerir_datos(u: dict = Depends(exige("encargado"))):
    """Nombre, apellidos, PIN y contraseña propuestos: el alta de un empleado no debería
    obligar a inventarse nada."""
    return {"nombre": secrets.choice(NOMBRES_PILA),
            "apellidos": f"{secrets.choice(APELLIDOS)} {secrets.choice(APELLIDOS)}",
            "pin": pin_libre(), "contrasena": contrasena_legible()}


@app.get("/api/empleados")
def listar_empleados(todos: bool = False, u: dict = Depends(exige("encargado"))):
    return q(f"""SELECT {CAMPOS_EMPLEADO} FROM empleados e
                 LEFT JOIN escalafones es ON es.clave = e.escalafon
                 {'' if todos else 'WHERE e.activo'}
                 ORDER BY es.nivel, e.nombre""")


def exigir_mando_sobre(u: dict, escalafon: str | None, verbo: str):
    """Nadie reparte galones por encima del suyo. Recordatorio de la escala: **a menor número,
    más mando** (1 = administrador), así que «estar por encima» es tener un número MENOR."""
    if not escalafon:
        return
    destino = q1("SELECT nivel, nombre FROM escalafones WHERE clave=%s", (escalafon,))
    if not destino:
        raise HTTPException(422, "Ese escalafón no existe")
    nivel = int(destino["nivel"])
    if nivel <= 3 and u["nivel"] > 2:            # tocar gestión es cosa de gerencia
        raise HTTPException(403, f"{verbo} un {destino['nombre']} es cosa del gerente o del "
                                 f"administrador; tú eres {u['escalafon_nombre']}")
    if nivel <= u["nivel"] and u["nivel"] > 1:   # ni a tu mismo escalafón ni por encima
        raise HTTPException(403, f"No puedes {verbo.lower()} a alguien de tu mismo escalafón o "
                                 "por encima")


@app.post("/api/empleados", status_code=201)
def crear_empleado(d: NuevoEmpleado, u: dict = Depends(exige("encargado"))):
    if d.rol not in ROLES:
        raise HTTPException(422, "Rol no válido")
    exigir_mando_sobre(u, d.escalafon, "Crear")
    pin = d.pin or pin_libre()
    if q1("SELECT id FROM empleados WHERE pin=%s", (pin,)):
        raise HTTPException(409, "Ese PIN ya está en uso")
    clara = d.contrasena or contrasena_legible()
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO empleados (nombre, apellidos, rol, escalafon, pin, contrasena,
                                              activo, alta_en)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,CURDATE())""",
                    (d.nombre.strip(), (d.apellidos or "").strip() or None, d.rol, d.escalafon,
                     pin, cifrar_clave(clara), d.activo))
        eid = cur.lastrowid
    # La contraseña en claro se enseña UNA vez, al crearla: después ya solo se puede regenerar.
    return {**empleado(eid), "contrasena_en_claro": clara}


@app.patch("/api/empleados/{eid}")
def editar_empleado(eid: int, d: CambioEmpleado, u: dict = Depends(exige("encargado"))):
    actual = q1("SELECT id, escalafon FROM empleados WHERE id=%s", (eid,))
    if not actual:
        raise HTTPException(404, "Empleado no encontrado")
    if d.rol and d.rol not in ROLES:
        raise HTTPException(422, "Rol no válido")
    if d.escalafon:
        exigir_mando_sobre(u, d.escalafon, "Ascender a")
        exigir_mando_sobre(u, actual["escalafon"], "Tocar a")
    if d.pin and q1("SELECT id FROM empleados WHERE pin=%s AND id<>%s", (d.pin, eid)):
        raise HTTPException(409, "Ese PIN ya está en uso")
    campos = {k: v for k, v in d.model_dump(exclude_unset=True).items() if v is not None}
    clara = campos.pop("contrasena", None)
    if clara:
        campos["contrasena"] = cifrar_clave(clara)
    if campos:
        q(f"UPDATE empleados SET {', '.join(f'{k}=%s' for k in campos)} WHERE id=%s",
          (*campos.values(), eid))
    return empleado(eid)


@app.post("/api/empleados/{eid}/contrasena")
def regenerar_contrasena(eid: int, u: dict = Depends(exige("encargado"))):
    """Devuelve una contraseña nueva en claro una sola vez; en la base solo queda el resumen."""
    actual = q1("SELECT id, escalafon FROM empleados WHERE id=%s", (eid,))
    if not actual:
        raise HTTPException(404, "Empleado no encontrado")
    exigir_mando_sobre(u, actual["escalafon"], "Cambiar la contraseña de")
    clara = contrasena_legible()
    q("UPDATE empleados SET contrasena=%s WHERE id=%s", (cifrar_clave(clara), eid))
    return {"id": eid, "contrasena_en_claro": clara}


@app.get("/api/nomina")
def nomina(u: dict = Depends(exige_nivel(2, "La nómina"))):
    """Lo que cobra cada escalafón sobre el sueldo del junior. El junior es el primer año:
    el 5 % del empleado base se ve aquí, no en un papel aparte."""
    base = int(ajustes_dict().get("sueldo_junior_cent", "120000"))
    filas = q("""SELECT es.clave, es.nombre, es.nivel, es.plus_pct, COUNT(e.id) AS personas
                 FROM escalafones es LEFT JOIN empleados e ON e.escalafon=es.clave AND e.activo
                 GROUP BY es.clave, es.nombre, es.nivel, es.plus_pct ORDER BY es.nivel""")
    for f in filas:
        f["sueldo_cent"] = round(base * (1 + float(f["plus_pct"]) / 100))
    return {"sueldo_junior_cent": base, "escalafones": filas}


@app.delete("/api/empleados/{eid}")
def baja_empleado(eid: int, u: dict = Depends(exige("encargado"))):
    """No se borra: se da de baja. Sus pedidos históricos deben seguir teniendo autor."""
    e = q1("SELECT id, escalafon FROM empleados WHERE id=%s", (eid,))
    if not e:
        raise HTTPException(404, "Empleado no encontrado")
    exigir_mando_sobre(u, e["escalafon"], "Dar de baja a")
    quedan = q1("""SELECT COUNT(*) n FROM empleados e JOIN escalafones es ON es.clave=e.escalafon
                   WHERE e.activo AND es.gestion AND e.id<>%s""", (eid,))["n"]
    if quedan == 0:
        raise HTTPException(409, "Debe quedar al menos una persona de gestión activa")
    q("UPDATE empleados SET activo=0 WHERE id=%s", (eid,))
    return {"ok": True}


# ─────────────── Ajustes del local ───────────────
def ajustes_dict():
    return {r["clave"]: r["valor"] for r in q("SELECT clave, valor FROM ajustes")}


@app.get("/api/ajustes")
def ver_ajustes(u: dict = Depends(usuario)):
    return ajustes_dict()


@app.put("/api/ajustes/{clave}")
def poner_ajuste(clave: str, d: Ajuste, u: dict = Depends(exige("encargado"))):
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
def emitir_factura(pid: int, d: DatosFactura, u: dict = Depends(exige("camarero", "encargado"))):
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
def cobros(fecha: str | None = None, u: dict = Depends(exige("camarero", "encargado"))):
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
def listar_facturas(fecha: str | None = None, buscar: str | None = None, u: dict = Depends(exige("camarero", "encargado"))):
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
def ver_factura(fid: int, u: dict = Depends(exige("camarero", "encargado"))):
    return factura_completa(fid)


@app.get("/api/pedidos/{pid}/documento")
def documento_pedido(pid: int, u: dict = Depends(exige("camarero", "encargado"))):
    """Datos que necesita la pantalla para pintar el ticket o la factura del pedido."""
    p = pedido_completo(pid)
    f = q1("SELECT id FROM facturas WHERE pedido_id=%s", (pid,))
    iva_pct = int(ajustes_dict().get("iva_pct", 10))
    base = round(p["total_cent"] / (1 + iva_pct / 100))
    return {"pedido": p, "local": ajustes_dict(), "iva_pct": iva_pct,
            "base_cent": base, "iva_cent": p["total_cent"] - base,
            "factura": factura_completa(f["id"]) if f else None}


# ─────────────── Arqueo de caja y cierre Z (encargado) ───────────────
# El informe dice lo que se ha vendido; el arqueo dice si el dinero está.
#   esperado   = fondo + ventas en efectivo + entradas - salidas
#   diferencia = contado - esperado   (negativo = falta dinero en el cajón)
DENOMINACIONES = (50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1)


def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def ventas_del_dia(dia: str) -> dict:
    """Lo que dicen los cobros de ese día, repartidos por método de pago."""
    por_metodo = q("""SELECT metodo, COUNT(*) AS pagos, SUM(importe_cent) AS total_cent
                      FROM pagos WHERE DATE(pagado_en)=%s GROUP BY metodo ORDER BY metodo""", (dia,))
    efectivo = sum(int(m["total_cent"]) for m in por_metodo if m["metodo"] == "efectivo")
    total = sum(int(m["total_cent"]) for m in por_metodo)
    tickets = q1("SELECT COUNT(*) AS n FROM pedidos WHERE estado='cobrado' AND DATE(cerrado_en)=%s",
                 (dia,))["n"]
    facturas = q1("""SELECT COUNT(*) AS emitidas,
                            MIN(CONCAT(serie, ejercicio, '/', LPAD(numero,5,'0'))) AS primera,
                            MAX(CONCAT(serie, ejercicio, '/', LPAD(numero,5,'0'))) AS ultima
                     FROM facturas WHERE DATE(emitida_en)=%s""", (dia,))
    anulados = q1("SELECT COUNT(*) AS n FROM pedidos WHERE estado='anulado' AND DATE(cerrado_en)=%s",
                  (dia,))["n"]
    iva_pct = int(ajustes_dict().get("iva_pct", 10))
    base = round(total / (1 + iva_pct / 100))
    return {"por_metodo": por_metodo, "ventas_efectivo_cent": efectivo, "ventas_total_cent": total,
            "tickets": tickets, "facturas": facturas, "anulados": anulados, "iva_pct": iva_pct,
            "base_cent": base, "iva_cent": total - base}


def arqueo_dia(dia: str):
    a = q1("""SELECT a.*, ea.nombre AS abierto_por_nombre, ec.nombre AS cerrado_por_nombre
              FROM arqueos a JOIN empleados ea ON ea.id=a.abierto_por
              LEFT JOIN empleados ec ON ec.id=a.cerrado_por WHERE a.fecha=%s""", (dia,))
    if a and a["estado"] == "cerrado":
        a["numero_z"] = f"Z{a['z_ejercicio']}/{a['z_numero']:05d}"
        a["recuento"] = json.loads(a["recuento"]) if a["recuento"] else None
        a["fondo_siguiente_cent"] = int(a["contado_cent"]) - int(a["retirada_cent"] or 0)
    return a


def estado_caja(dia: str) -> dict:
    """Foto de la caja de un día: lo vendido, lo movido a mano y lo que debería haber."""
    a = arqueo_dia(dia)
    v = ventas_del_dia(dia)
    movimientos, entradas, salidas = [], 0, 0
    if a:
        movimientos = q("""SELECT mc.*, e.nombre AS empleado FROM movimientos_caja mc
                           JOIN empleados e ON e.id=mc.empleado_id
                           WHERE mc.arqueo_id=%s ORDER BY mc.id""", (a["id"],))
        entradas = sum(int(m["importe_cent"]) for m in movimientos if m["tipo"] == "entrada")
        salidas = sum(int(m["importe_cent"]) for m in movimientos if m["tipo"] == "salida")
    fondo = int(a["fondo_cent"]) if a else 0
    esperado = fondo + v["ventas_efectivo_cent"] + entradas - salidas
    if a and a["estado"] == "cerrado":
        esperado = int(a["esperado_cent"])          # el cierre Z congela las cifras
    abiertos = q("""SELECT p.id, p.tipo, p.cliente, m.nombre AS mesa, v.total_cent
                    FROM pedidos p JOIN v_totales_pedido v ON v.pedido_id=p.id
                    LEFT JOIN mesas m ON m.id=p.mesa_id
                    WHERE p.estado='abierto' ORDER BY p.id""") if dia == _hoy() else []
    return {"fecha": dia, "arqueo": a, "movimientos": movimientos,
            "entradas_cent": entradas, "salidas_cent": salidas,
            "fondo_cent": fondo, "esperado_cent": esperado,
            "fondo_sugerido_cent": int(ajustes_dict().get("fondo_caja_cent", 15000)),
            "pedidos_abiertos": abiertos, "denominaciones": list(DENOMINACIONES),
            "local": ajustes_dict(), **v}


@app.get("/api/arqueo")
def ver_caja(fecha: str | None = None, u: dict = Depends(exige("camarero", "encargado"))):
    return estado_caja(fecha or _hoy())


@app.post("/api/arqueo/apertura", status_code=201)
async def abrir_caja(d: AperturaCaja, u: dict = Depends(exige("encargado"))):
    """Declara el fondo de cambio con el que empieza el servicio."""
    dia = _hoy()
    if arqueo_dia(dia):
        raise HTTPException(409, "La caja de hoy ya está abierta")
    q("INSERT INTO arqueos (fecha, fondo_cent, abierto_por) VALUES (%s,%s,%s)",
      (dia, d.fondo_cent, u["id"]))
    await hub.emitir("caja")
    return estado_caja(dia)


@app.post("/api/arqueo/movimientos", status_code=201)
async def anotar_movimiento(d: MovimientoCaja, u: dict = Depends(exige("camarero", "encargado"))):
    """Efectivo que entra o sale del cajón sin ser una venta (proveedor, cambio, banco)."""
    if d.tipo not in ("entrada", "salida"):
        raise HTTPException(422, "El movimiento es 'entrada' o 'salida'")
    a = arqueo_dia(_hoy())
    if not a:
        raise HTTPException(409, "No hay caja abierta: ábrela declarando el fondo")
    if a["estado"] == "cerrado":
        raise HTTPException(409, "La caja del día ya está cerrada")
    q("""INSERT INTO movimientos_caja (arqueo_id, tipo, importe_cent, motivo, empleado_id)
         VALUES (%s,%s,%s,%s,%s)""", (a["id"], d.tipo, d.importe_cent, d.motivo.strip(), u["id"]))
    await hub.emitir("caja")
    return estado_caja(_hoy())


@app.delete("/api/arqueo/movimientos/{mid}")
async def borrar_movimiento(mid: int, u: dict = Depends(exige("encargado"))):
    m = q1("""SELECT mc.id, a.estado FROM movimientos_caja mc JOIN arqueos a ON a.id=mc.arqueo_id
              WHERE mc.id=%s""", (mid,))
    if not m:
        raise HTTPException(404, "Movimiento no encontrado")
    if m["estado"] == "cerrado":
        raise HTTPException(409, "La caja de ese día ya está cerrada")
    q("DELETE FROM movimientos_caja WHERE id=%s", (mid,))
    await hub.emitir("caja")
    return estado_caja(_hoy())


@app.post("/api/arqueo/cierre")
async def cerrar_caja(d: CierreCaja, forzar: bool = False, u: dict = Depends(exige("encargado"))):
    """Cierre Z: cuenta el cajón, calcula el descuadre y firma el día. No tiene vuelta atrás."""
    dia = _hoy()
    est = estado_caja(dia)
    a = est["arqueo"]
    if not a:
        raise HTTPException(409, "No hay caja abierta hoy")
    if a["estado"] == "cerrado":
        raise HTTPException(409, f"La caja de hoy ya se cerró ({a['numero_z']})")
    if est["pedidos_abiertos"] and not forzar:
        ids = ", ".join("#" + str(p["id"]) for p in est["pedidos_abiertos"])
        raise HTTPException(409, f"Hay pedidos sin cobrar ({ids}): cóbralos o anúlalos antes de cerrar")
    if d.recuento:
        suma = sum(int(valor) * int(n) for valor, n in d.recuento.items())
        if suma != d.contado_cent:
            raise HTTPException(422, f"El recuento suma {suma / 100:.2f} € y el efectivo contado es "
                                     f"{d.contado_cent / 100:.2f} €")
    if d.retirada_cent > d.contado_cent:
        raise HTTPException(422, "No se puede retirar más efectivo del que hay en el cajón")
    ejercicio = datetime.now().year
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(z_numero), 0) + 1 AS n FROM arqueos WHERE z_ejercicio=%s FOR UPDATE",
                    (ejercicio,))
        numero = cur.fetchone()["n"]
        cur.execute("""UPDATE arqueos SET estado='cerrado', z_ejercicio=%s, z_numero=%s,
                         contado_cent=%s, esperado_cent=%s, diferencia_cent=%s,
                         ventas_efectivo_cent=%s, ventas_total_cent=%s, tickets=%s,
                         retirada_cent=%s, recuento=%s, notas=%s, cerrado_por=%s, cerrado_en=NOW()
                       WHERE id=%s AND estado='abierto'""",
                    (ejercicio, numero, d.contado_cent, est["esperado_cent"],
                     d.contado_cent - est["esperado_cent"], est["ventas_efectivo_cent"],
                     est["ventas_total_cent"], est["tickets"], d.retirada_cent,
                     json.dumps(d.recuento) if d.recuento else None,
                     (d.notas or "").strip() or None, u["id"], a["id"]))
        if cur.rowcount != 1:
            raise HTTPException(409, "La caja se ha cerrado desde otra pantalla")
    await hub.emitir("caja")
    return estado_caja(dia)


@app.get("/api/arqueos")
def listar_arqueos(desde: str | None = None, hasta: str | None = None,
                   u: dict = Depends(exige("encargado"))):
    """Histórico de cierres: para ver si el descuadre es un día suelto o una costumbre."""
    donde, args = [], []
    if desde:
        donde.append("a.fecha >= %s")
        args.append(desde)
    if hasta:
        donde.append("a.fecha <= %s")
        args.append(hasta)
    filtro = ("WHERE " + " AND ".join(donde)) if donde else ""
    return q(f"""SELECT a.id, a.fecha, a.estado, a.fondo_cent, a.contado_cent, a.esperado_cent,
                        a.diferencia_cent, a.ventas_total_cent, a.tickets, a.retirada_cent,
                        a.cerrado_en, ec.nombre AS cerrado_por_nombre,
                        CASE WHEN a.z_numero IS NULL THEN NULL
                             ELSE CONCAT('Z', a.z_ejercicio, '/', LPAD(a.z_numero, 5, '0')) END AS numero_z
                 FROM arqueos a LEFT JOIN empleados ec ON ec.id=a.cerrado_por
                 {filtro} ORDER BY a.fecha DESC LIMIT 60""", args)


@app.get("/api/arqueo/{aid}")
def ver_arqueo(aid: int, u: dict = Depends(exige("encargado"))):
    a = q1("SELECT fecha FROM arqueos WHERE id=%s", (aid,))
    if not a:
        raise HTTPException(404, "Arqueo no encontrado")
    return estado_caja(a["fecha"].strftime("%Y-%m-%d"))


# ─────────────── Alérgenos, protocolo, inventario y fotos ───────────────
class NuevoAlergeno(BaseModel):
    clave: str = Field(pattern=r"^[a-z0-9_]{2,20}$")
    nombre: str = Field(min_length=2, max_length=40)
    icono: str = Field("⚠", max_length=8)
    gravedad: str = "grave"
    presente_en: str = Field("", max_length=200)
    protocolo: str = Field(min_length=10)
    orden: int = Field(0, ge=0, le=127)


class CambioAlergeno(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    icono: str | None = Field(None, max_length=8)
    gravedad: str | None = None
    presente_en: str | None = Field(None, max_length=200)
    protocolo: str | None = Field(None, min_length=10)
    orden: int | None = Field(None, ge=0, le=127)


GRAVEDADES = ("leve", "grave", "muy_grave")


@app.get("/api/alergenos")
def listar_alergenos(u: dict = Depends(usuario)):
    """El catálogo entero, con su protocolo. Lo puede leer cualquiera con sesión: el camarero
    que tiene delante a alguien con una reacción no está para pedir permisos."""
    return q("SELECT * FROM alergenos ORDER BY orden, nombre")


@app.get("/api/protocolo")
def protocolo(u: dict = Depends(usuario)):
    return {"general": ajustes_dict().get("protocolo_general", ""),
            "alergenos": q("SELECT * FROM alergenos ORDER BY orden, nombre")}


@app.post("/api/alergenos", status_code=201)
async def crear_alergeno(d: NuevoAlergeno, u: dict = Depends(exige("encargado"))):
    if d.gravedad not in GRAVEDADES:
        raise HTTPException(422, "Gravedad no válida")
    if q1("SELECT clave FROM alergenos WHERE clave=%s", (d.clave,)):
        raise HTTPException(409, "Ya existe ese alérgeno")
    q("""INSERT INTO alergenos (clave, nombre, icono, gravedad, presente_en, protocolo, orden)
         VALUES (%s,%s,%s,%s,%s,%s,%s)""",
      (d.clave, d.nombre.strip(), d.icono, d.gravedad, d.presente_en, d.protocolo, d.orden))
    await hub.emitir("carta")
    return q1("SELECT * FROM alergenos WHERE clave=%s", (d.clave,))


@app.patch("/api/alergenos/{clave}")
async def editar_alergeno(clave: str, d: CambioAlergeno, u: dict = Depends(exige("encargado"))):
    if not q1("SELECT clave FROM alergenos WHERE clave=%s", (clave,)):
        raise HTTPException(404, "Alérgeno no encontrado")
    if d.gravedad and d.gravedad not in GRAVEDADES:
        raise HTTPException(422, "Gravedad no válida")
    campos = {k: v for k, v in d.model_dump(exclude_unset=True).items() if v is not None}
    if campos:
        q(f"UPDATE alergenos SET {', '.join(f'{k}=%s' for k in campos)} WHERE clave=%s",
          (*campos.values(), clave))
    await hub.emitir("carta")
    return q1("SELECT * FROM alergenos WHERE clave=%s", (clave,))


@app.get("/api/inventario")
def buscar_inventario(buscar: str | None = None, u: dict = Depends(usuario)):
    """Búsqueda para el autocompletado de la carta. Desde tres caracteres, que es cuando la
    consulta empieza a decir algo; con menos se devuelve el principio del catálogo."""
    if buscar and len(buscar.strip()) >= 3:
        patron = f"%{buscar.strip()}%"
        return q("""SELECT * FROM inventario WHERE activo AND (nombre LIKE %s OR sku LIKE %s)
                    ORDER BY nombre LIMIT 25""", (patron, patron))
    return q("SELECT * FROM inventario WHERE activo ORDER BY nombre LIMIT 25")


def sincronizar_alergenos(pid: int, claves: list[str] | None) -> None:
    """La tabla N:M manda; el campo de texto del producto se regenera a partir de ella para que
    el TPV y la cocina, que leen texto, no se enteren del cambio."""
    if claves is None:
        return
    validas = {a["clave"]: a["nombre"] for a in q("SELECT clave, nombre FROM alergenos")}
    malas = [c for c in claves if c not in validas]
    if malas:
        raise HTTPException(422, f"Alérgeno desconocido: {', '.join(malas)}")
    q("DELETE FROM producto_alergenos WHERE producto_id=%s", (pid,))
    for c in claves:
        q("INSERT INTO producto_alergenos (producto_id, alergeno) VALUES (%s,%s)", (pid, c))
    texto = ", ".join(validas[c] for c in claves) or None
    q("UPDATE productos SET alergenos=%s WHERE id=%s", (texto[:120] if texto else None, pid))


def alergenos_de(pid: int) -> list[str]:
    return [f["alergeno"] for f in
            q("SELECT alergeno FROM producto_alergenos WHERE producto_id=%s", (pid,))]


def precio_sugerido(coste_cent: int) -> int:
    """Precio de carta a partir del coste: x3,2 (escandallo de barra) y redondeo a los 95
    céntimos de siempre, que es como se ponen los precios en una carta de verdad."""
    bruto = max(150, int(coste_cent * 3.2))
    return ((bruto + 99) // 100) * 100 - 5


@app.post("/api/carta/precios")
async def generar_precios(todos: bool = False, u: dict = Depends(exige("encargado"))):
    """Pone precio a la carta de un golpe. Por defecto solo a lo que está a cero; con
    `todos=true` recalcula la carta entera desde el coste del inventario."""
    filas = q("""SELECT p.id, p.precio_cent, i.coste_cent
                 FROM productos p LEFT JOIN inventario i ON i.id = p.inventario_id
                 WHERE p.activo""" + ("" if todos else " AND p.precio_cent = 0"))
    tocados = 0
    for f in filas:
        coste = f["coste_cent"] or 0
        nuevo = precio_sugerido(coste) if coste else max(295, f["precio_cent"] or 295)
        if nuevo != f["precio_cent"]:
            q("UPDATE productos SET precio_cent=%s WHERE id=%s", (nuevo, f["id"]))
            tocados += 1
    await hub.emitir("carta")
    return {"revisados": len(filas), "cambiados": tocados}


# Colores estables por nombre: el mismo plato sale siempre con la misma pinta.
def _tono(semilla: int, base: int) -> str:
    return f"hsl({(semilla * 47 + base) % 360} 65% 55%)"


@app.get("/api/productos/{prid}/foto.svg")
def foto_producto(prid: int):
    """Foto generada: si nadie ha subido una, el sistema dibuja el plato. Es comida de una
    cantina minera, así que un cuenco con formas raras es más honrado que una foto de stock."""
    pr = q1("SELECT id, nombre FROM productos WHERE id=%s", (prid,))
    if not pr:
        raise HTTPException(404, "Producto no encontrado")
    semilla = sum(ord(c) for c in pr["nombre"])
    trozos = []
    for i in range(3 + semilla % 4):
        cx = 60 + (semilla * (i + 3) % 80)
        cy = 95 + (semilla * (i + 7) % 35)
        r = 12 + (semilla * (i + 2) % 16)
        trozos.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_tono(semilla, i * 60)}" '
                      f'opacity="0.9"/>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="200" height="160">
  <rect width="200" height="160" fill="#1e2127"/>
  <ellipse cx="100" cy="115" rx="86" ry="34" fill="#2b2f36"/>
  <ellipse cx="100" cy="110" rx="74" ry="27" fill="{_tono(semilla, 200)}" opacity="0.25"/>
  {''.join(trozos)}
  <path d="M30 60 Q100 20 170 60" stroke="{_tono(semilla, 120)}" stroke-width="5" fill="none"
        opacity="0.6"/>
  <text x="100" y="150" text-anchor="middle" font-family="sans-serif" font-size="12"
        fill="#9aa3b2">{esc_xml(pr['nombre'])}</text>
</svg>"""
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})


def esc_xml(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))[:28]


# ─────────────── Secciones de cocina y pantallas de KDS ───────────────
class NuevaEstacion(BaseModel):
    clave: str = Field(pattern=r"^[a-z0-9_]{2,20}$")
    nombre: str = Field(min_length=2, max_length=40)
    icono: str = Field("🍳", max_length=8)
    orden: int = Field(0, ge=0, le=127)


class CambioEstacion(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    icono: str | None = Field(None, max_length=8)
    orden: int | None = Field(None, ge=0, le=127)
    activa: bool | None = None


class NuevaPantalla(BaseModel):
    clave: str = Field(pattern=r"^[a-z0-9_]{2,20}$")
    nombre: str = Field(min_length=2, max_length=40)
    icono: str = Field("🔔", max_length=8)
    estaciones: str = Field("", max_length=200)          # vacío = todas (pase)
    orden: int = Field(0, ge=0, le=127)


class CambioPantalla(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    icono: str | None = Field(None, max_length=8)
    estaciones: str | None = Field(None, max_length=200)
    orden: int | None = Field(None, ge=0, le=127)
    activa: bool | None = None


@app.get("/api/estaciones")
def listar_estaciones(todas: bool = False, u: dict = Depends(usuario)):
    return q("SELECT * FROM estaciones" + ("" if todas else " WHERE activa") + " ORDER BY orden, clave")


@app.post("/api/estaciones", status_code=201)
async def crear_estacion(d: NuevaEstacion, u: dict = Depends(exige("encargado"))):
    if q1("SELECT clave FROM estaciones WHERE clave=%s", (d.clave,)):
        raise HTTPException(409, "Ya existe una sección con esa clave")
    q("INSERT INTO estaciones (clave, nombre, icono, orden) VALUES (%s,%s,%s,%s)",
      (d.clave, d.nombre.strip(), d.icono, d.orden))
    await hub.emitir("cocina_config")
    return q1("SELECT * FROM estaciones WHERE clave=%s", (d.clave,))


@app.patch("/api/estaciones/{clave}")
async def editar_estacion(clave: str, d: CambioEstacion, u: dict = Depends(exige("encargado"))):
    if not q1("SELECT clave FROM estaciones WHERE clave=%s", (clave,)):
        raise HTTPException(404, "Sección no encontrada")
    campos = {k: v for k, v in d.model_dump(exclude_unset=True).items() if v is not None}
    if campos:
        q(f"UPDATE estaciones SET {', '.join(f'{k}=%s' for k in campos)} WHERE clave=%s",
          (*campos.values(), clave))
    await hub.emitir("cocina_config")
    return q1("SELECT * FROM estaciones WHERE clave=%s", (clave,))


@app.delete("/api/estaciones/{clave}")
async def quitar_estacion(clave: str, u: dict = Depends(exige("encargado"))):
    """No se borra si hay carta colgando de ella: se desactiva, que es lo honrado."""
    n = q1("SELECT COUNT(*) n FROM productos WHERE estacion=%s AND activo", (clave,))["n"]
    if n:
        q("UPDATE estaciones SET activa=0 WHERE clave=%s", (clave,))
        await hub.emitir("cocina_config")
        return {"desactivada": True, "productos": n}
    q("DELETE FROM estaciones WHERE clave=%s", (clave,))
    await hub.emitir("cocina_config")
    return {"borrada": True}


@app.get("/api/kds-pantallas")
def listar_pantallas(todas: bool = False, u: dict = Depends(usuario)):
    filas = q("SELECT * FROM kds_pantallas" + ("" if todas else " WHERE activa") + " ORDER BY orden, clave")
    nombres = {e["clave"]: e["nombre"] for e in q("SELECT clave, nombre FROM estaciones")}
    for f in filas:
        claves = [c for c in f["estaciones"].split(",") if c]
        f["secciones"] = claves
        f["detalle"] = " + ".join(nombres.get(c, c) for c in claves) or "todas las secciones"
    return filas


@app.post("/api/kds-pantallas", status_code=201)
async def crear_pantalla(d: NuevaPantalla, u: dict = Depends(exige("encargado"))):
    if q1("SELECT clave FROM kds_pantallas WHERE clave=%s", (d.clave,)):
        raise HTTPException(409, "Ya existe una pantalla con esa clave")
    claves_de_pantalla(d.estaciones, None)               # valida las secciones antes de guardar
    q("INSERT INTO kds_pantallas (clave, nombre, icono, estaciones, orden) VALUES (%s,%s,%s,%s,%s)",
      (d.clave, d.nombre.strip(), d.icono, d.estaciones, d.orden))
    await hub.emitir("cocina_config")
    return q1("SELECT * FROM kds_pantallas WHERE clave=%s", (d.clave,))


@app.patch("/api/kds-pantallas/{clave}")
async def editar_pantalla(clave: str, d: CambioPantalla, u: dict = Depends(exige("encargado"))):
    if not q1("SELECT clave FROM kds_pantallas WHERE clave=%s", (clave,)):
        raise HTTPException(404, "Pantalla no encontrada")
    campos = {k: v for k, v in d.model_dump(exclude_unset=True).items() if v is not None}
    if "estaciones" in campos:
        claves_de_pantalla(campos["estaciones"], None)
    if campos:
        q(f"UPDATE kds_pantallas SET {', '.join(f'{k}=%s' for k in campos)} WHERE clave=%s",
          (*campos.values(), clave))
    await hub.emitir("cocina_config")
    return q1("SELECT * FROM kds_pantallas WHERE clave=%s", (clave,))


@app.delete("/api/kds-pantallas/{clave}")
async def quitar_pantalla(clave: str, u: dict = Depends(exige("encargado"))):
    q("DELETE FROM kds_pantallas WHERE clave=%s", (clave,))
    await hub.emitir("cocina_config")
    return {"borrada": True}


# ─────────────── Plano del local en 2D (editable) ───────────────
TIPOS_PLANO = ("muro", "zona", "mesa", "equipo", "puerta", "barra")


class ElementoPlano(BaseModel):
    tipo: str
    nombre: str = Field("", max_length=40)
    mesa_id: int | None = None
    puesto: str | None = Field(None, max_length=20)
    x: int = Field(0, ge=0, le=1000)
    y: int = Field(0, ge=0, le=1000)
    ancho: int = Field(60, ge=4, le=1000)
    alto: int = Field(60, ge=4, le=1000)
    forma: str = "rect"
    icono: str = Field("", max_length=8)
    color: str = Field("#3a3f49", max_length=7)
    z: int = Field(1, ge=0, le=20)


class CambioElemento(BaseModel):
    nombre: str | None = Field(None, max_length=40)
    mesa_id: int | None = None
    puesto: str | None = Field(None, max_length=20)
    x: int | None = Field(None, ge=0, le=1000)
    y: int | None = Field(None, ge=0, le=1000)
    ancho: int | None = Field(None, ge=4, le=1000)
    alto: int | None = Field(None, ge=4, le=1000)
    forma: str | None = None
    icono: str | None = Field(None, max_length=8)
    color: str | None = Field(None, max_length=7)


def _se_pisan(a: dict, b: dict) -> bool:
    return (a["x"] < b["x"] + b["ancho"] and a["x"] + a["ancho"] > b["x"]
            and a["y"] < b["y"] + b["alto"] and a["y"] + a["alto"] > b["y"])


def comprobar_sitio(elem: dict, excluir: int | None = None) -> None:
    """Lo que ocupa sitio físico (mesas, equipos, barra) no puede quedar dentro de un muro.
    Es la regla que pidió el encargado: no se coloca una silla en mitad de un tabique."""
    if elem["tipo"] in ("muro", "zona", "puerta"):
        return
    for muro in q("SELECT * FROM plano_elementos WHERE tipo='muro'"):
        if excluir and muro["id"] == excluir:
            continue
        if _se_pisan(elem, muro):
            raise HTTPException(422, f"Ahí hay un muro ({muro['nombre'] or 'sin nombre'}): "
                                     "eso no se puede colocar dentro de la pared")


@app.get("/api/plano")
def ver_plano(u: dict = Depends(usuario)):
    """El plano entero, con las mesas enlazadas y su estado de ocupación."""
    elementos = q("SELECT * FROM plano_elementos ORDER BY z, id")
    ocupadas = {m["mesa_id"]: m for m in q("""SELECT p.mesa_id, p.id AS pedido_id, p.abierto_en
                                              FROM pedidos p WHERE p.estado='abierto' AND p.mesa_id IS NOT NULL""")}
    mesas = {m["id"]: m for m in q("SELECT * FROM mesas")}
    for e in elementos:
        if e["tipo"] == "mesa" and e["mesa_id"] in mesas:
            m = mesas[e["mesa_id"]]
            e["mesa"] = {"nombre": m["nombre"], "zona": m["zona"], "plazas": m["plazas"],
                         "pedido_id": (ocupadas.get(m["id"]) or {}).get("pedido_id")}
    return {"elementos": elementos,
            "mesas_sin_colocar": [m for m in mesas.values()
                                  if m["id"] not in {e["mesa_id"] for e in elementos}]}


@app.post("/api/plano/elementos", status_code=201)
async def crear_elemento(d: ElementoPlano, u: dict = Depends(exige("encargado"))):
    if d.tipo not in TIPOS_PLANO:
        raise HTTPException(422, "Tipo de elemento desconocido")
    comprobar_sitio(d.model_dump())
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO plano_elementos
                       (tipo, nombre, mesa_id, puesto, x, y, ancho, alto, forma, icono, color, z)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (d.tipo, d.nombre, d.mesa_id, d.puesto, d.x, d.y, d.ancho, d.alto,
                     d.forma, d.icono, d.color, d.z))
        eid = cur.lastrowid
    await hub.emitir("plano")
    return q1("SELECT * FROM plano_elementos WHERE id=%s", (eid,))


@app.patch("/api/plano/elementos/{eid}")
async def mover_elemento(eid: int, d: CambioElemento, u: dict = Depends(exige("encargado"))):
    actual = q1("SELECT * FROM plano_elementos WHERE id=%s", (eid,))
    if not actual:
        raise HTTPException(404, "Elemento no encontrado")
    campos = {k: v for k, v in d.model_dump(exclude_unset=True).items() if v is not None}
    comprobar_sitio({**actual, **campos}, excluir=eid)
    if campos:
        q(f"UPDATE plano_elementos SET {', '.join(f'{k}=%s' for k in campos)} WHERE id=%s",
          (*campos.values(), eid))
    await hub.emitir("plano")
    return q1("SELECT * FROM plano_elementos WHERE id=%s", (eid,))


@app.delete("/api/plano/elementos/{eid}")
async def borrar_elemento(eid: int, u: dict = Depends(exige("encargado"))):
    q("DELETE FROM plano_elementos WHERE id=%s", (eid,))
    await hub.emitir("plano")
    return {"ok": True}


@app.post("/api/plano/generar")
async def generar_plano(u: dict = Depends(exige("encargado"))):
    """Dibuja un local entero de partida y reparte dentro las mesas que ya existen.

    Es el plano de un local de verdad leído desde arriba: fachada con su puerta, comedor a la
    izquierda, mirador acristalado abajo, atraque (barra) en el centro, cocina al fondo a la
    derecha con sus equipos, y el paso entre sala y cocina. A partir de aquí se arrastra.
    """
    q("DELETE FROM plano_elementos")
    muro = "#4a5160"
    piezas = [
        # perímetro
        ("muro", "Fachada norte", None, None, 10, 10, 980, 14, "rect", "", muro, 0),
        ("muro", "Fachada sur", None, None, 10, 976, 980, 14, "rect", "", muro, 0),
        ("muro", "Muro oeste", None, None, 10, 10, 14, 980, "rect", "", muro, 0),
        ("muro", "Muro este", None, None, 976, 10, 14, 980, "rect", "", muro, 0),
        # tabique de cocina y su paso
        ("muro", "Tabique de cocina", None, None, 620, 24, 14, 470, "rect", "", muro, 0),
        ("puerta", "Paso a cocina", None, None, 620, 494, 14, 120, "rect", "↔", "#f1c40f", 1),
        ("puerta", "Entrada", None, None, 120, 976, 120, 14, "rect", "⇕", "#f1c40f", 1),
        # zonas
        ("zona", "Comedor presurizado", None, "comedor", 24, 24, 380, 470, "rect", "", "#2471a3", 0),
        ("zona", "Mirador de la fractura", None, "mirador", 24, 510, 380, 460, "rect", "", "#1f618d", 0),
        ("zona", "Atraque", None, "atraque", 420, 24, 190, 946, "rect", "", "#5499c7", 0),
        ("zona", "Cocina", None, None, 640, 24, 336, 700, "rect", "", "#7d6608", 0),
        ("zona", "Oficina", None, "oficina", 640, 740, 160, 230, "rect", "", "#566573", 0),
        ("zona", "Recogida", None, "recogida", 812, 740, 164, 230, "rect", "", "#b9770e", 0),
        # mobiliario fijo
        ("barra", "Barra", None, "caja", 440, 60, 150, 300, "rect", "▤", "#117864", 2),
        # equipos de cocina, cada uno atado a su sección
        ("equipo", "Placa térmica", None, "plancha", 660, 60, 140, 110, "rect", "🍔", "#c0392b", 2),
        ("equipo", "Fritura", None, "freidora", 820, 60, 140, 110, "rect", "🍟", "#d68910", 2),
        ("equipo", "Cámara fría", None, "frios", 660, 200, 140, 110, "rect", "🥗", "#8e44ad", 2),
        ("equipo", "Barra de oxígeno", None, "barra", 820, 200, 140, 110, "rect", "🥤", "#229954", 2),
        ("equipo", "Pase", None, "pase", 660, 340, 300, 90, "rect", "🔔", "#7d6608", 2),
        ("equipo", "Lavado", None, None, 660, 450, 140, 100, "rect", "🚿", "#34495e", 2),
        ("equipo", "Cámara de despensa", None, None, 820, 450, 140, 100, "rect", "📦", "#34495e", 2),
    ]
    with conn() as c, c.cursor() as cur:
        cur.executemany("""INSERT INTO plano_elementos
            (tipo, nombre, mesa_id, puesto, x, y, ancho, alto, forma, icono, color, z)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", piezas)
        # Las mesas de verdad, repartidas dentro de la zona que les toca por su `zona`.
        cajas = {"sala": (60, 70, 330, 400), "terraza": (60, 560, 330, 380), "barra": (455, 400, 120, 520)}
        contador = {k: 0 for k in cajas}
        for m in q("SELECT * FROM mesas ORDER BY zona, id"):
            x0, y0, anchura, altura = cajas.get(m["zona"], cajas["sala"])
            i = contador.get(m["zona"], 0)
            contador[m["zona"]] = i + 1
            columnas = max(1, anchura // 120)
            cx = x0 + (i % columnas) * 120
            cy = y0 + (i // columnas) * 120
            cy = min(cy, y0 + max(0, altura - 90))
            cur.execute("""INSERT INTO plano_elementos
                (tipo, nombre, mesa_id, puesto, x, y, ancho, alto, forma, icono, color, z)
                VALUES ('mesa',%s,%s,NULL,%s,%s,%s,%s,%s,'',%s,3)""",
                        (m["nombre"], m["id"], cx, cy, 86, 86,
                         "circ" if m["zona"] != "barra" else "rect",
                         "#2b2f36"))
        c.commit()
    await hub.emitir("plano")
    return ver_plano(u)


# ─────────────── Plano de la cantina: quién está dónde ───────────────
class Destino(BaseModel):
    puesto: str | None = None                       # None = quitar del plano
    x: int | None = Field(None, ge=0, le=100)       # posición de la ficha, en % del plano
    y: int | None = Field(None, ge=0, le=100)


@app.get("/api/puestos")
def listar_puestos(u: dict = Depends(usuario)):
    """El plano: cajas, colores y a qué pantalla entra quien esté en cada una."""
    return q("SELECT * FROM puestos ORDER BY orden, clave")


@app.get("/api/plantilla")
def plantilla(u: dict = Depends(exige("encargado"))):
    """Quién está en cada puesto ahora mismo, con la sesión abierta si la tiene."""
    return q("""SELECT e.id, e.nombre, e.rol, e.puesto, e.mapa_x, e.mapa_y,
                       p.nombre AS puesto_nombre, p.gui, p.rol_operativo,
                       MAX(s.ultimo_uso) AS ultimo_uso
                FROM empleados e
                LEFT JOIN puestos p ON p.clave = e.puesto
                LEFT JOIN sesiones s ON s.empleado_id = e.id AND s.caduca_en > NOW()
                WHERE e.activo
                GROUP BY e.id, p.nombre, p.gui, p.rol_operativo
                ORDER BY e.nombre""")


@app.put("/api/empleados/{eid}/puesto")
async def mover_empleado(eid: int, d: Destino, u: dict = Depends(exige("encargado"))):
    """Suelta la ficha de un empleado en un puesto del plano. Sus pantallas se enteran
    por el WebSocket y se van solas a la GUI que les toca."""
    e = q1("SELECT id, nombre FROM empleados WHERE id=%s AND activo", (eid,))
    if not e:
        raise HTTPException(404, "Empleado no encontrado")
    if d.puesto and not q1("SELECT clave FROM puestos WHERE clave=%s", (d.puesto,)):
        raise HTTPException(422, "Ese puesto no está en el plano")
    q("UPDATE empleados SET puesto=%s, mapa_x=%s, mapa_y=%s WHERE id=%s",
      (d.puesto, d.x, d.y, eid))
    await hub.emitir("plantilla", empleado_id=eid, puesto=d.puesto)
    return q1("""SELECT e.id, e.nombre, e.rol, e.puesto, e.mapa_x, e.mapa_y,
                        p.nombre AS puesto_nombre, p.gui, p.rol_operativo
                 FROM empleados e LEFT JOIN puestos p ON p.clave=e.puesto
                 WHERE e.id=%s""", (eid,))


def sitio_en_puesto(p: dict, n: int) -> tuple[int, int]:
    """Dónde cae la ficha número `n` dentro de la caja de un puesto: dos por fila, sin pisarse."""
    x = p["x"] + 3 + (n % 2) * max(6, p["ancho"] // 2)
    y = p["y"] + 9 + (n // 2) * 8
    return (min(x, p["x"] + p["ancho"] - 4), min(y, p["y"] + p["alto"] - 3))


@app.post("/api/plantilla/reparto")
async def repartir_plantilla(u: dict = Depends(exige("encargado"))):
    """Coloca a todo el mundo en su sitio de un botón: cada rol a sus puestos, por turnos,
    para que no se amontonen todos en la plancha. Es un punto de partida razonable para
    abrir el servicio; luego el encargado arrastra lo que quiera."""
    puestos = q("SELECT * FROM puestos ORDER BY orden, clave")
    por_rol = {"camarero": [p for p in puestos if p["rol_operativo"] == "camarero"],
               "cocina":   [p for p in puestos if p["rol_operativo"] == "cocina"]}
    oficina = next((p for p in puestos if p["clave"] == "oficina"), None)
    descanso = next((p for p in puestos if p["clave"] == "descanso"), None)
    empleados = q("SELECT id, nombre, rol FROM empleados WHERE activo ORDER BY rol, id")
    turno = {"camarero": 0, "cocina": 0}
    ocupacion: dict[str, int] = {}
    colocados = 0
    for e in empleados:
        if e["rol"] == "encargado":
            destino = oficina
        else:
            sitios = por_rol.get(e["rol"]) or []
            if not sitios:
                destino = descanso
            else:
                destino = sitios[turno[e["rol"]] % len(sitios)]
                turno[e["rol"]] += 1
        if not destino:
            continue
        n = ocupacion.get(destino["clave"], 0)
        ocupacion[destino["clave"]] = n + 1
        x, y = sitio_en_puesto(destino, n)
        q("UPDATE empleados SET puesto=%s, mapa_x=%s, mapa_y=%s WHERE id=%s",
          (destino["clave"], x, y, e["id"]))
        colocados += 1
    await hub.emitir("plantilla", reparto=True)
    return {"colocados": colocados, "plantilla": plantilla(u)}


# ─────────────── Simulación de actividad (demo) ───────────────
@app.get("/api/simulacion")
def ver_simulacion(u: dict = Depends(usuario)):
    return simulacion.resumen()


@app.post("/api/simulacion/{accion}")
async def mandar_simulacion(accion: str, ritmo: float | None = None,
                            u: dict = Depends(exige("encargado"))):
    """play arranca o reanuda, pause congela, reset para y borra lo que la simulación creó."""
    if accion == "play":
        return await simulacion.play(ritmo)
    if accion == "pause":
        return await simulacion.pause()
    if accion == "reset":
        return await simulacion.reset()
    raise HTTPException(422, "Acción desconocida: play, pause o reset")


@app.on_event("shutdown")
async def parar_simulacion():
    if simulacion.tarea:
        simulacion.tarea.cancel()


# ─────────────── La sala mientras ocurre ───────────────
# Tres cosas que el sistema ya sabía pero no contaba: cuánta gente hay dentro, quién lleva
# esperando y cuánto dura cada tramo de la visita. No hace falta ninguna cámara: todo esto
# está fechado en la base de datos desde el primer día.
class Comensales(BaseModel):
    comensales: int = Field(ge=1, le=30)


@app.patch("/api/pedidos/{pid}/comensales")
async def poner_comensales(pid: int, d: Comensales, u: dict = Depends(exige("camarero", "encargado"))):
    exigir_abierto(pid)
    q("UPDATE pedidos SET comensales=%s WHERE id=%s", (d.comensales, pid))
    await hub.emitir("mesas")
    return pedido_completo(pid)


def _minutos(clave: str, por_defecto: int) -> int:
    try:
        return int(ajustes_dict().get(clave, por_defecto))
    except ValueError:
        return por_defecto


@app.get("/api/sala")
def sala(u: dict = Depends(exige("camarero", "encargado"))):
    """Foto del servicio ahora mismo: ocupación y quién lleva esperando.

    Las alertas no miran el reloj del plato, sino el del cliente: una mesa a la que nadie ha
    tomado nota, una cuenta que nadie cobra o un plato listo que nadie recoge. Un plato puede
    salir en seis minutos y el cliente llevar veinte esperando; eso es lo que aquí se ve.
    """
    espera_nota = _minutos("sala_espera_nota", 6)
    espera_cuenta = _minutos("sala_espera_cuenta", 8)
    espera_pase = _minutos("sala_espera_pase", 5)

    mesas = q("""SELECT m.id, m.nombre, m.zona, m.plazas,
                        p.id AS pedido_id, p.abierto_en, p.comensales, e.nombre AS camarero,
                        v.total_cent,
                        TIMESTAMPDIFF(MINUTE, p.abierto_en, NOW()) AS minutos
                 FROM mesas m
                 LEFT JOIN pedidos p ON p.mesa_id=m.id AND p.estado='abierto'
                 LEFT JOIN empleados e ON e.id=p.empleado_id
                 LEFT JOIN v_totales_pedido v ON v.pedido_id=p.id
                 ORDER BY m.zona, m.id""")

    estados = {}
    for f in q("""SELECT l.pedido_id, l.estado, COUNT(*) n,
                         MAX(TIMESTAMPDIFF(MINUTE, l.lista_en, NOW())) AS min_listo
                  FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id
                  WHERE p.estado='abierto' AND l.estado<>'anulada'
                  GROUP BY l.pedido_id, l.estado"""):
        estados.setdefault(f["pedido_id"], {})[f["estado"]] = f

    alertas, ocupadas, comensales = [], 0, 0
    for m in mesas:
        if not m["pedido_id"]:
            m["estado"] = "libre"
            continue
        ocupadas += 1
        comensales += m["comensales"] or 0
        por_estado = estados.get(m["pedido_id"], {})
        m["lineas"] = {k: v["n"] for k, v in por_estado.items()}
        if not por_estado:
            m["estado"] = "sin_pedir"
            if m["minutos"] >= espera_nota:
                alertas.append({"tipo": "sin_nota", "mesa": m["nombre"], "pedido_id": m["pedido_id"],
                                "minutos": m["minutos"],
                                "texto": f"Mesa {m['nombre']}: {m['minutos']} min sentados y nadie les ha tomado nota"})
        elif set(por_estado) <= {"servida"}:
            m["estado"] = "esperando_cuenta"
            if m["minutos"] >= espera_cuenta:
                alertas.append({"tipo": "cuenta", "mesa": m["nombre"], "pedido_id": m["pedido_id"],
                                "minutos": m["minutos"], "importe_cent": m["total_cent"],
                                "texto": f"Mesa {m['nombre']}: todo servido y la cuenta sin cobrar"})
        elif "lista" in por_estado:
            m["estado"] = "pase"
            espera = por_estado["lista"].get("min_listo") or 0
            if espera >= espera_pase:
                alertas.append({"tipo": "pase", "mesa": m["nombre"], "pedido_id": m["pedido_id"],
                                "minutos": espera,
                                "texto": f"Mesa {m['nombre']}: hay {por_estado['lista']['n']} plato(s) listos desde hace {espera} min"})
        elif "pendiente" in por_estado:
            m["estado"] = "tomando_nota"
        else:
            m["estado"] = "en_cocina"

    alertas.sort(key=lambda a: a["minutos"], reverse=True)
    llevar = q("""SELECT COUNT(*) n FROM pedidos WHERE estado='abierto' AND tipo='llevar'""")[0]["n"]
    return {
        "ahora": datetime.now(),
        "mesas": mesas,
        "libres": len(mesas) - ocupadas,
        "ocupadas": ocupadas,
        "comensales": comensales,
        "por_mesa": round(comensales / ocupadas, 1) if ocupadas and comensales else None,
        "para_llevar": llevar,
        "alertas": alertas,
        "umbrales": {"nota": espera_nota, "cuenta": espera_cuenta, "pase": espera_pase},
    }


@app.get("/api/informe/tiempos")
def informe_tiempos(fecha: str | None = None, u: dict = Depends(exige("encargado"))):
    """Cuánto dura cada tramo de la visita, con las marcas de tiempo que ya existen.

    abrir mesa → tomar nota → cocina → recoger del pase → cobrar. Medir solo la cocina engaña:
    un plato de seis minutos no salva una mesa que esperó veinte a que la atendieran.
    """
    dia = fecha or datetime.now().strftime("%Y-%m-%d")
    tramos = q1("""SELECT
        COUNT(DISTINCT p.id) AS visitas,
        ROUND(AVG(TIMESTAMPDIFF(SECOND, p.abierto_en, l.primera))) AS seg_nota,
        ROUND(AVG(TIMESTAMPDIFF(SECOND, l.primera, l.ultima_lista))) AS seg_cocina,
        ROUND(AVG(TIMESTAMPDIFF(SECOND, l.ultima_lista, p.cerrado_en))) AS seg_mesa,
        ROUND(AVG(TIMESTAMPDIFF(SECOND, p.abierto_en, p.cerrado_en))) AS seg_visita,
        ROUND(AVG(p.comensales), 1) AS comensales_medios
      FROM pedidos p
      JOIN (SELECT pedido_id, MIN(enviada_en) AS primera, MAX(lista_en) AS ultima_lista
            FROM lineas_pedido WHERE estado<>'anulada' GROUP BY pedido_id) l ON l.pedido_id=p.id
      WHERE p.estado='cobrado' AND DATE(p.cerrado_en)=%s AND l.primera IS NOT NULL""", (dia,))

    por_franja = q("""SELECT HOUR(p.abierto_en) AS hora, COUNT(*) AS visitas,
                             ROUND(AVG(TIMESTAMPDIFF(SECOND, p.abierto_en, p.cerrado_en))/60) AS min_visita
                      FROM pedidos p WHERE p.estado='cobrado' AND DATE(p.cerrado_en)=%s
                      GROUP BY hora ORDER BY hora""", (dia,))

    lentas = q("""SELECT p.id, m.nombre AS mesa, e.nombre AS camarero,
                         TIMESTAMPDIFF(MINUTE, p.abierto_en, p.cerrado_en) AS minutos,
                         v.total_cent
                  FROM pedidos p LEFT JOIN mesas m ON m.id=p.mesa_id
                  JOIN empleados e ON e.id=p.empleado_id
                  JOIN v_totales_pedido v ON v.pedido_id=p.id
                  WHERE p.estado='cobrado' AND DATE(p.cerrado_en)=%s
                  ORDER BY minutos DESC LIMIT 5""", (dia,))
    return {"fecha": dia, "tramos": tramos, "por_franja": por_franja, "mas_lentas": lentas}


# ─────────────── Cliente (sin sesión, solo desde la LAN del local) ───────────────
# Todo lo de aquí lo abre el cliente con su teléfono tras leer el QR de la mesa. No hay PIN,
# así que no se expone ni un dato interno: ni estación de cocina, ni empleados, ni importes
# ajenos. Y nada de lo que se pulse llega a cocina por sí solo: primero lo acepta un camarero.
def _cliente_puede_pedir() -> bool:
    return ajustes_dict().get("cliente_pedidos", "si") == "si"


@app.get("/api/publico/local")
def publico_local():
    a = ajustes_dict()
    return {"nombre": a.get("local_nombre"), "mensaje": a.get("cliente_mensaje", ""),
            "pedidos": _cliente_puede_pedir()}


@app.get("/api/publico/alergenos")
def publico_alergenos():
    """Leyenda de alérgenos: icono, nombre y gravedad. El protocolo de actuación NO sale aquí:
    eso es para el personal, no para la carta del cliente."""
    return q("SELECT clave, nombre, icono, gravedad FROM alergenos ORDER BY orden, clave")


@app.get("/api/publico/carta")
def publico_carta():
    """La carta tal y como la ve un cliente: sin estación, sin bajas y sin nada interno."""
    cats = q("SELECT id, nombre, color FROM categorias WHERE activa ORDER BY orden, id")
    prods = q("""SELECT id, categoria_id, nombre, precio_cent, alergenos, disponible, foto
                 FROM productos WHERE activo ORDER BY categoria_id, orden, id""")
    marcas = {}
    for r in q("""SELECT pa.producto_id, pa.alergeno FROM producto_alergenos pa"""):
        marcas.setdefault(r["producto_id"], []).append(r["alergeno"])
    for p in prods:
        p["alergeno_claves"] = marcas.get(p["id"], [])
    for c in cats:
        c["productos"] = [p for p in prods if p["categoria_id"] == c["id"]]
    return [c for c in cats if c["productos"]]


@app.get("/api/publico/destacados")
def publico_destacados():
    """Lo que el local quiere enseñar primero: los más vendidos de los últimos días que
    además estén disponibles hoy. Sin nada que configurar a mano."""
    filas = q("""SELECT pr.id, pr.nombre, pr.precio_cent, pr.foto, c.nombre AS categoria, c.color,
                        SUM(l.cantidad) AS unidades
                 FROM lineas_pedido l
                 JOIN productos pr ON pr.id=l.producto_id
                 JOIN categorias c ON c.id=pr.categoria_id
                 JOIN pedidos p ON p.id=l.pedido_id
                 WHERE p.estado='cobrado' AND p.cerrado_en >= NOW() - INTERVAL 7 DAY
                   AND pr.activo AND pr.disponible AND c.activa
                 GROUP BY pr.id ORDER BY unidades DESC LIMIT 6""")
    if filas:
        return filas
    return q("""SELECT pr.id, pr.nombre, pr.precio_cent, pr.foto, c.nombre AS categoria, c.color,
                       0 AS unidades
                FROM productos pr JOIN categorias c ON c.id=pr.categoria_id
                WHERE pr.activo AND pr.disponible AND c.activa ORDER BY pr.orden, pr.id LIMIT 6""")


@app.get("/api/publico/mesas")
def publico_mesas():
    """Solo nombres, para que el cliente diga dónde está sentado si el QR no lo trae."""
    return q("SELECT id, nombre, zona FROM mesas ORDER BY zona, id")


@app.post("/api/publico/solicitudes", status_code=201)
async def publico_solicitar(d: Solicitud, request: Request):
    if not _cliente_puede_pedir():
        raise HTTPException(409, "Ahora mismo no se admiten pedidos desde la mesa")
    if d.mesa_id and not q1("SELECT id FROM mesas WHERE id=%s", (d.mesa_id,)):
        raise HTTPException(404, "Esa mesa no existe")
    # Freno sencillo contra el niño que se aburre pulsando: 3 solicitudes por mesa sin resolver.
    if d.mesa_id:
        abiertas = q1("""SELECT COUNT(*) n FROM solicitudes
                         WHERE mesa_id=%s AND estado='pendiente'""", (d.mesa_id,))["n"]
        if abiertas >= 3:
            raise HTTPException(429, "Ya hay pedidos de esta mesa esperando confirmación")

    lineas = []
    for l in d.lineas:
        pr = q1("""SELECT id, nombre, precio_cent, disponible FROM productos
                   WHERE id=%s AND activo""", (l.producto_id,))
        if not pr:
            raise HTTPException(404, "Ese producto ya no está en la carta")
        if not pr["disponible"]:
            raise HTTPException(409, f"{pr['nombre']} está agotado")
        lineas.append((l, pr))

    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO solicitudes (mesa_id, cliente, nota, origen_ip)
                       VALUES (%s,%s,%s,%s)""",
                    (d.mesa_id, (d.cliente or "").strip() or None, d.nota,
                     request.client.host if request.client else None))
        sid = cur.lastrowid
        for l, _ in lineas:
            cur.execute("""INSERT INTO solicitud_lineas (solicitud_id, producto_id, cantidad, notas)
                           VALUES (%s,%s,%s,%s)""", (sid, l.producto_id, l.cantidad, l.notas))
    await hub.emitir("solicitudes", solicitud_id=sid)          # suena en el TPV
    total = sum(l.cantidad * pr["precio_cent"] for l, pr in lineas)
    return {"id": sid, "estado": "pendiente", "total_cent": total,
            "lineas": [{"nombre": pr["nombre"], "cantidad": l.cantidad,
                        "precio_cent": pr["precio_cent"]} for l, pr in lineas]}


@app.get("/api/publico/solicitudes/{sid}")
def publico_estado_solicitud(sid: int):
    """Lo que el cliente puede seguir desde su teléfono: su propia comanda y nada más."""
    s = q1("""SELECT s.id, s.estado, s.pedido_id, s.creada_en, m.nombre AS mesa
              FROM solicitudes s LEFT JOIN mesas m ON m.id=s.mesa_id WHERE s.id=%s""", (sid,))
    if not s:
        raise HTTPException(404, "No encuentro ese pedido")
    s["lineas"] = q("""SELECT sl.cantidad, sl.notas, p.nombre, p.precio_cent
                       FROM solicitud_lineas sl JOIN productos p ON p.id=sl.producto_id
                       WHERE sl.solicitud_id=%s""", (sid,))
    s["total_cent"] = sum(l["cantidad"] * l["precio_cent"] for l in s["lineas"])
    if s["pedido_id"]:
        cocina = q("""SELECT estado, COUNT(*) n FROM lineas_pedido
                      WHERE pedido_id=%s AND estado<>'anulada' GROUP BY estado""", (s["pedido_id"],))
        s["cocina"] = {c["estado"]: c["n"] for c in cocina}
    return s


# ─────────────── Solicitudes (sala) ───────────────
@app.get("/api/solicitudes")
def listar_solicitudes(u: dict = Depends(exige("camarero", "encargado"))):
    filas = q("""SELECT s.*, m.nombre AS mesa FROM solicitudes s
                 LEFT JOIN mesas m ON m.id=s.mesa_id
                 WHERE s.estado='pendiente' ORDER BY s.creada_en""")
    for f in filas:
        f["lineas"] = q("""SELECT sl.cantidad, sl.notas, sl.producto_id, p.nombre, p.precio_cent
                           FROM solicitud_lineas sl JOIN productos p ON p.id=sl.producto_id
                           WHERE sl.solicitud_id=%s""", (f["id"],))
        f["total_cent"] = sum(l["cantidad"] * l["precio_cent"] for l in f["lineas"])
    return filas


@app.post("/api/solicitudes/{sid}/aceptar")
async def aceptar_solicitud(sid: int, u: dict = Depends(exige("camarero", "encargado"))):
    """La convierte en pedido de verdad: a partir de aquí es una comanda como cualquier otra."""
    s = q1("SELECT * FROM solicitudes WHERE id=%s", (sid,))
    if not s:
        raise HTTPException(404, "Solicitud no encontrada")
    if s["estado"] != "pendiente":
        raise HTTPException(409, f"Esa solicitud ya está {s['estado']}")
    lineas = q("""SELECT sl.*, p.precio_cent, p.estacion, p.disponible, p.nombre
                  FROM solicitud_lineas sl JOIN productos p ON p.id=sl.producto_id
                  WHERE sl.solicitud_id=%s""", (sid,))
    agotados = [l["nombre"] for l in lineas if not l["disponible"]]
    if agotados:
        raise HTTPException(409, "Se ha agotado: " + ", ".join(agotados))

    abierto = q1("SELECT id FROM pedidos WHERE mesa_id=%s AND estado='abierto'", (s["mesa_id"],)) \
        if s["mesa_id"] else None
    with conn() as c, c.cursor() as cur:
        if abierto:
            pid = abierto["id"]                               # se suma a lo que ya tiene la mesa
        else:
            cur.execute("""INSERT INTO pedidos (tipo, mesa_id, empleado_id, cliente)
                           VALUES (%s,%s,%s,%s)""",
                        ("sala" if s["mesa_id"] else "llevar", s["mesa_id"], u["id"], s["cliente"]))
            pid = cur.lastrowid
        for l in lineas:
            cur.execute("""INSERT INTO lineas_pedido
                           (pedido_id, producto_id, cantidad, precio_cent, notas, estacion)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (pid, l["producto_id"], l["cantidad"], l["precio_cent"],
                         l["notas"], l["estacion"]))
        cur.execute("""UPDATE solicitudes SET estado='aceptada', pedido_id=%s,
                       atendida_por=%s, resuelta_en=NOW() WHERE id=%s""", (pid, u["id"], sid))
    await hub.emitir("mesas")
    await hub.emitir("solicitudes", solicitud_id=sid)
    # El teléfono del cliente escucha el canal público, que no lleva datos: solo «vuelve a
    # mirar». Así ve que su comanda ha sido confirmada sin esperar al siguiente sondeo.
    await hub.emitir_publico("solicitud")
    return pedido_completo(pid)


@app.post("/api/solicitudes/{sid}/rechazar")
async def rechazar_solicitud(sid: int, u: dict = Depends(exige("camarero", "encargado"))):
    s = q1("SELECT estado FROM solicitudes WHERE id=%s", (sid,))
    if not s:
        raise HTTPException(404, "Solicitud no encontrada")
    if s["estado"] != "pendiente":
        raise HTTPException(409, f"Esa solicitud ya está {s['estado']}")
    q("""UPDATE solicitudes SET estado='rechazada', atendida_por=%s, resuelta_en=NOW()
         WHERE id=%s""", (u["id"], sid))
    await hub.emitir("solicitudes", solicitud_id=sid)
    await hub.emitir_publico("solicitud")
    return {"ok": True}


# ─────────────── Frontend estático ───────────────
# ─────────────── Idempotencia: el mismo acto, una sola vez ───────────────
# Este middleware se declara ANTES que el de la LAN a propósito: en FastAPI el último que se
# añade envuelve a los anteriores, así que declarándolo aquí queda por DENTRO de la guarda de
# red y nunca contesta a nadie de fuera con una respuesta guardada.
def _dias_idempotencia() -> int:
    fila = q1("SELECT valor FROM ajustes WHERE clave='idempotencia_dias'")
    try:
        return max(1, int(fila["valor"])) if fila else 3
    except ValueError:
        return 3


@app.middleware("http")
async def idempotencia(request: Request, call_next):
    """Repetir una petición con la misma clave devuelve la respuesta de la primera vez.

    Lo necesita el TPV sin red: al reconectar reenvía lo que apuntó el camarero, y no puede
    saber si la petición de antes llegó a ejecutarse o se perdió con la respuesta. La clave la
    inventa el cliente UNA vez por acción (no por intento), así que reenviar es gratis.

    Solo se guardan las respuestas buenas (2xx). Un 409 «esa mesa ya está cobrada» no se guarda:
    si la situación cambia, la segunda vez merece respuesta nueva.
    """
    clave = request.headers.get("Idempotency-Key")
    if not clave or request.method not in ("POST", "PATCH", "PUT", "DELETE"):
        return await call_next(request)
    if len(clave) > 64:
        return JSONResponse({"detail": "Clave de idempotencia demasiado larga"}, status_code=422)

    previa = q1("SELECT estado, respuesta FROM idempotencia WHERE clave=%s", (clave,))
    if previa:
        return Response(previa["respuesta"], status_code=previa["estado"],
                        media_type="application/json", headers={"X-Idempotencia": "repetida"})

    resp = await call_next(request)
    cuerpo = b"".join([trozo async for trozo in resp.body_iterator])
    if 200 <= resp.status_code < 300 and len(cuerpo) <= 1_000_000:
        cabecera = request.headers.get("authorization", "")
        quien = usuario_de_token(cabecera[7:]) if cabecera.lower().startswith("bearer ") else None
        try:
            q("""INSERT IGNORE INTO idempotencia (clave, ruta, empleado_id, estado, respuesta)
                 VALUES (%s,%s,%s,%s,%s)""",
              (clave, f"{request.method} {request.url.path}"[:160],
               quien["id"] if quien else None, resp.status_code, cuerpo.decode("utf-8", "replace")))
            q("DELETE FROM idempotencia WHERE creada_en < NOW() - INTERVAL %s DAY", (_dias_idempotencia(),))
        except Exception:
            # Que no se pueda anotar la clave no es motivo para negarle la comanda al camarero:
            # el trabajo ya está hecho y la respuesta es buena. Lo que se pierde es la red de
            # seguridad contra un reenvío, y eso es preferible a un 500 con la cocina esperando.
            pass
    return Response(cuerpo, status_code=resp.status_code, headers=dict(resp.headers),
                    media_type=resp.media_type)


# ─────────────── Solo LAN ───────────────
# El sistema es de un local: no tiene por qué contestar a nadie de fuera. Dos capas:
#   1) el servicio escucha solo en la IP de la red local (ver kds-tpv.service);
#   2) esta guarda rechaza cualquier cliente fuera de las redes permitidas.
# La segunda existe porque la primera se la salta un reenvío de puertos del router.
@app.middleware("http")
async def solo_lan(request: Request, call_next):
    """Puerta de la casa. Se mira la IP real del cliente, NUNCA una cabecera:
    `X-Forwarded-For` la escribe quien llama y se falsifica en un segundo."""
    cliente = request.client.host if request.client else None
    if not es_de_la_lan(cliente):
        return JSONResponse({"detail": "Este servicio solo atiende a la red local"}, status_code=403)
    return await call_next(request)


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
