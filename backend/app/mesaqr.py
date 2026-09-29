"""El QR de la mesa y la visita que abre.

Tres reglas que gobiernan todo lo de aquí:

  · **Un código, un uso.** Se canjea una vez y queda quemado. Si dos teléfonos leen el mismo QR
    a la vez, el segundo recibe un «ya no vale» y tiene que usar el de unirse.
  · **Vida corta y variable.** Cada código dura entre `qr_min_seg` y `qr_max_seg` segundos, al
    azar, más un margen de gracia por si alguien lo lee justo cuando la pantalla cambia. Que el
    intervalo no sea fijo quita la gracia de esperar el siguiente.
  · **Quien mide el tiempo es el servidor.** Las pantallas no llevan reloj de verdad.

La visita es la estancia del grupo, no el pedido. Un grupo se sienta, tarda en pedir, pide en dos
tandas y se va: eso es una visita con un pedido dentro, y no al revés.
"""
import secrets
from datetime import datetime

from fastapi import HTTPException

from .db import conn, q, q1

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # sin I, O, 0, 1: se confunden al leerlos


def _ajustes() -> dict:
    return {f["clave"]: f["valor"] for f in q("SELECT clave, valor FROM ajustes")}


def config() -> dict:
    a = _ajustes()

    def entero(clave, por_defecto):
        try:
            return int(a.get(clave, por_defecto))
        except (TypeError, ValueError):
            return por_defecto

    minimo = max(3, entero("qr_min_seg", 5))
    maximo = max(minimo, entero("qr_max_seg", 50))
    return {
        "activo": str(a.get("qr_mesas_activo", "si")).strip().lower() in ("si", "sí", "1", "true"),
        "min_seg": minimo,
        "max_seg": maximo,
        "margen_seg": entero("qr_margen_seg", 10),
        "cierre_min": entero("visita_cierre_min", 10),
    }


def _clave(largo: int) -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(largo))


# ─────────────── Pantallas ───────────────
def pantalla_de_secreto(secreto: str | None) -> dict | None:
    if not secreto:
        return None
    p = q1("""SELECT p.id, p.mesa_id, p.nombre, p.activa, m.nombre AS mesa
              FROM mesa_pantallas p JOIN mesas m ON m.id=p.mesa_id
              WHERE p.secreto=%s""", (secreto,))
    return p if p and p["activa"] else None


def alta_pantalla(mesa_id: int, nombre: str | None) -> dict:
    if not q1("SELECT id FROM mesas WHERE id=%s", (mesa_id,)):
        raise HTTPException(404, "Esa mesa no existe")
    secreto = secrets.token_hex(32)
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO mesa_pantallas (mesa_id, nombre, secreto) VALUES (%s,%s,%s)",
                    (mesa_id, (nombre or "").strip() or None, secreto))
        pid = cur.lastrowid
    # El secreto se enseña **una sola vez**, al darla de alta: es lo que hay que grabar en la
    # pantalla. Después ya no se puede volver a ver, solo cambiar.
    return {"id": pid, "mesa_id": mesa_id, "secreto": secreto}


def listar_pantallas() -> list[dict]:
    return q("""SELECT p.id, p.mesa_id, p.nombre, p.activa, p.visto_en, p.firmware,
                       m.nombre AS mesa,
                       TIMESTAMPDIFF(SECOND, p.visto_en, NOW()) AS hace_seg
                FROM mesa_pantallas p JOIN mesas m ON m.id=p.mesa_id
                ORDER BY m.zona, m.id""")


def latido(pantalla_id: int, firmware: str | None) -> None:
    q("UPDATE mesa_pantallas SET visto_en=NOW(), firmware=COALESCE(%s, firmware) WHERE id=%s",
      (firmware, pantalla_id))


# ─────────────── Códigos ───────────────
def visita_activa(mesa_id: int) -> dict | None:
    return q1("SELECT * FROM visitas WHERE mesa_id=%s AND estado='activa'", (mesa_id,))


def emitir(pantalla: dict, cfg: dict) -> dict:
    """Un código nuevo para esa pantalla, con lo que tiene que durar.

    Si la mesa ya tiene visita abierta no se emite nada nuevo: la pantalla enseña el código de
    unirse hasta que el grupo se vaya. Así el QR rotativo es lo que abre la mesa, y solo eso.
    """
    latido(pantalla["id"], None)
    visita = visita_activa(pantalla["mesa_id"])
    if visita:
        return {"modo": "union", "codigo": visita["codigo_union"], "segundos": 30,
                "mesa": pantalla["mesa"], "visita_id": visita["id"]}

    segundos = secrets.randbelow(cfg["max_seg"] - cfg["min_seg"] + 1) + cfg["min_seg"]
    codigo = _clave(12)
    q("""INSERT INTO mesa_codigos (codigo, mesa_id, pantalla_id, caduca_en)
         VALUES (%s,%s,%s, NOW() + INTERVAL %s SECOND)""",
      (codigo, pantalla["mesa_id"], pantalla["id"], segundos + cfg["margen_seg"]))
    # Limpieza perezosa: los códigos de ayer no le importan a nadie.
    q("DELETE FROM mesa_codigos WHERE emitido_en < NOW() - INTERVAL 2 DAY AND canjeado_en IS NULL")
    return {"modo": "rotativo", "codigo": codigo, "segundos": segundos,
            "mesa": pantalla["mesa"], "visita_id": None}


# ─────────────── Canje y visitas ───────────────
def abrir_visita(mesa_id: int, reserva_id: int | None = None) -> dict:
    # Si la mesa ya tenía un pedido abierto (lo apuntó el camarero antes de que nadie leyera el
    # QR), la visita nace enganchada a él: es la misma gente y la misma cuenta.
    abierto = q1("SELECT id FROM pedidos WHERE mesa_id=%s AND estado='abierto'", (mesa_id,))
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO visitas (mesa_id, codigo_union, reserva_id, pedido_id)
                       VALUES (%s,%s,%s,%s)""",
                    (mesa_id, _clave(8), reserva_id, abierto["id"] if abierto else None))
        vid = cur.lastrowid
    return q1("SELECT * FROM visitas WHERE id=%s", (vid,))


def unir_dispositivo(visita_id: int, alias: str | None, cliente_id: int | None) -> str:
    token = secrets.token_hex(32)
    q("""INSERT INTO visita_dispositivos (token, visita_id, cliente_id, alias, ultimo_visto)
         VALUES (%s,%s,%s,%s,NOW())""",
      (token, visita_id, cliente_id, (alias or "").strip()[:40] or None))
    return token


def canjear(codigo: str, alias: str | None, cliente_id: int | None) -> dict:
    """Leer el QR rotativo: abre la visita de esa mesa (o se une a la que ya haya) y devuelve el
    token del teléfono."""
    codigo = (codigo or "").strip().upper()
    c = q1("""SELECT c.*, m.nombre AS mesa FROM mesa_codigos c JOIN mesas m ON m.id=c.mesa_id
              WHERE c.codigo=%s""", (codigo,))
    if not c:
        raise HTTPException(404, "Ese código no vale; vuelve a leer el de la mesa")
    if c["canjeado_en"]:
        raise HTTPException(409, "Ese código ya lo ha usado alguien; en la pantalla hay otro")
    if c["caduca_en"] < datetime.now():
        raise HTTPException(410, "Ese código ha caducado; lee el que hay ahora en la pantalla")

    visita = visita_activa(c["mesa_id"]) or abrir_visita(c["mesa_id"])
    q("UPDATE mesa_codigos SET canjeado_en=NOW(), visita_id=%s WHERE codigo=%s",
      (visita["id"], codigo))
    token = unir_dispositivo(visita["id"], alias, cliente_id)
    return {"token": token, **estado(visita["id"])}


def unirse(codigo_union: str, alias: str | None, cliente_id: int | None) -> dict:
    """El QR fijo que enseña la pantalla mientras la mesa está ocupada: para los rezagados."""
    codigo_union = (codigo_union or "").strip().upper()
    v = q1("SELECT * FROM visitas WHERE codigo_union=%s AND estado='activa'", (codigo_union,))
    if not v:
        raise HTTPException(404, "Esa mesa ya no está abierta")
    token = unir_dispositivo(v["id"], alias, cliente_id)
    return {"token": token, **estado(v["id"])}


def de_token(token: str | None) -> dict | None:
    """El dispositivo y su visita, si el token sigue valiendo."""
    if not token:
        return None
    d = q1("""SELECT d.token, d.visita_id, d.alias, d.cliente_id, v.estado
              FROM visita_dispositivos d JOIN visitas v ON v.id=d.visita_id
              WHERE d.token=%s""", (token,))
    if not d or d["estado"] != "activa":
        return None
    q("UPDATE visita_dispositivos SET ultimo_visto=NOW() WHERE token=%s", (token,))
    return d


def estado(visita_id: int) -> dict:
    v = q1("""SELECT v.id, v.mesa_id, v.pedido_id, v.estado, v.codigo_union, v.abierta_en,
                     m.nombre AS mesa, m.zona
              FROM visitas v JOIN mesas m ON m.id=v.mesa_id WHERE v.id=%s""", (visita_id,))
    if not v:
        raise HTTPException(404, "Esa mesa ya no está abierta")
    v["comensales"] = q1("""SELECT COUNT(*) n FROM visita_dispositivos WHERE visita_id=%s""",
                         (visita_id,))["n"]
    return v


def cerrar(visita_id: int) -> None:
    q("UPDATE visitas SET estado='cerrada', cerrada_en=NOW() WHERE id=%s AND estado='activa'",
      (visita_id,))
    # Los tokens de los teléfonos mueren con la visita: nadie sigue «en la mesa 3» al día
    # siguiente desde su casa.
    q("DELETE FROM visita_dispositivos WHERE visita_id=%s", (visita_id,))


def cerrar_por_mesa(mesa_id: int) -> int:
    filas = q("SELECT id FROM visitas WHERE mesa_id=%s AND estado='activa'", (mesa_id,))
    for f in filas:
        cerrar(f["id"])
    return len(filas)


def cerrables(cfg: dict) -> list[dict]:
    """Visitas que ya se pueden cerrar solas: la cuenta está saldada (o no llegó a haberla) y ha
    pasado el rato de cortesía. Lo que no se cierra nunca solo es una mesa con saldo pendiente."""
    return q("""SELECT v.id FROM visitas v
                LEFT JOIN pedidos p ON p.id=v.pedido_id
                WHERE v.estado='activa'
                  AND (
                    -- cuenta saldada (o anulada) y pasado el rato de cortesía
                    (p.id IS NOT NULL AND p.estado IN ('cobrado','anulado')
                     AND p.cerrado_en < NOW() - INTERVAL %s MINUTE)
                    -- o nadie ha vuelto a mirar el móvil en horas: la mesa se quedó abierta
                    OR (v.pedido_id IS NULL AND v.abierta_en < NOW() - INTERVAL 4 HOUR
                        AND NOT EXISTS (SELECT 1 FROM visita_dispositivos d
                                        WHERE d.visita_id=v.id
                                          AND d.ultimo_visto > NOW() - INTERVAL 2 HOUR))
                  )""",
             (cfg["cierre_min"],))


def listar_activas() -> list[dict]:
    filas = q("""SELECT v.id, v.mesa_id, v.pedido_id, v.abierta_en, v.codigo_union,
                        m.nombre AS mesa, m.zona,
                        TIMESTAMPDIFF(MINUTE, v.abierta_en, NOW()) AS minutos,
                        (SELECT COUNT(*) FROM visita_dispositivos d WHERE d.visita_id=v.id) AS moviles
                 FROM visitas v JOIN mesas m ON m.id=v.mesa_id
                 WHERE v.estado='activa' ORDER BY v.abierta_en""")
    return filas
