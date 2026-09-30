"""Reservas de mesa con pedido adelantado.

Reglas del encargo, y por qué están donde están:

  · **Quince minutos de antelación como mínimo.** Es lo que da margen a la sala para reaccionar;
    el número se puede cambiar en ajustes, pero la comprobación vive en el servidor, nunca en el
    teléfono del cliente.
  · **Una mesa no se reserva dos veces a la vez.** Una reserva ocupa su mesa durante
    `reserva_duracion_min`, así que dos reservas de la misma mesa tienen que estar separadas por
    esa duración. La comprobación se hace al crear, y otra vez al sentar: entre medias puede
    haber entrado alguien por la puerta.
  · **El pedido adelantado no se cobra por adelantado.** Se queda esperando y entra en cocina
    `reserva_margen_cocina_min` antes de la hora, para que la comida esté hecha al sentarse. El
    precio se congela al pasar a `lineas_pedido`, como en cualquier comanda: manda el de ese
    momento, no el del día que se reservó.

Aquí está la lógica que se puede probar sin servidor. Los endpoints, el almacén y los avisos a
las pantallas viven en `main.py`, que es quien tiene el hub y la sesión.
"""
import secrets
from datetime import datetime, time, timedelta

from .db import q, q1

ZONAS = ("sala", "terraza", "barra")


# ─────────────── Ajustes ───────────────
def _ajustes() -> dict:
    return {f["clave"]: f["valor"] for f in q("SELECT clave, valor FROM ajustes")}


def _entero(a: dict, clave: str, por_defecto: int) -> int:
    try:
        return int(a.get(clave, por_defecto))
    except (TypeError, ValueError):
        return por_defecto


def config() -> dict:
    a = _ajustes()
    return {
        "activas": str(a.get("reservas_activas", "si")).strip().lower() in ("si", "sí", "1", "true"),
        "antelacion_min": _entero(a, "reserva_antelacion_min", 15),
        "duracion_min": _entero(a, "reserva_duracion_min", 90),
        "margen_cocina_min": _entero(a, "reserva_margen_cocina_min", 10),
        "max_dias": _entero(a, "reserva_max_dias", 30),
        "paso_min": max(5, _entero(a, "reserva_paso_min", 30)),
        "horario": str(a.get("reserva_horario", "13:00-16:00,20:00-23:30")),
    }


def tramos_horario(texto: str) -> list[tuple[time, time]]:
    """«13:00-16:00,20:00-23:30» → [(13:00, 16:00), (20:00, 23:30)].

    Lo que no se entienda se ignora en silencio: un ajuste mal escrito no puede tumbar la
    pantalla de reservas, como mucho deja el día sin huecos y se ve al momento.
    """
    tramos = []
    for parte in texto.split(","):
        trozos = parte.strip().split("-")
        if len(trozos) != 2:
            continue
        try:
            desde = time.fromisoformat(trozos[0].strip())
            hasta = time.fromisoformat(trozos[1].strip())
        except ValueError:
            continue
        if desde < hasta:
            tramos.append((desde, hasta))
    return tramos


def franjas_del_dia(dia: datetime, cfg: dict) -> list[datetime]:
    """Las horas a las que se puede pedir mesa ese día, según horario y paso."""
    salida = []
    for desde, hasta in tramos_horario(cfg["horario"]):
        actual = datetime.combine(dia.date(), desde)
        fin = datetime.combine(dia.date(), hasta)
        while actual <= fin - timedelta(minutes=cfg["paso_min"]):
            salida.append(actual)
            actual += timedelta(minutes=cfg["paso_min"])
    return salida


def en_horario(hora: datetime, cfg: dict) -> bool:
    for desde, hasta in tramos_horario(cfg["horario"]):
        if desde <= hora.time() <= hasta:
            return True
    return False


# ─────────────── Mesas y solapes ───────────────
ESTADOS_VIVOS = ("pendiente", "confirmada", "sentada")


def mesas_para(comensales: int, zona: str | None) -> list[dict]:
    """Mesas donde cabe ese grupo, de la más ajustada a la más grande.

    Se da la más pequeña donde quepa: sentar a dos en la mesa de seis es quedarse sin la de
    seis para el grupo que llame después.
    """
    args: list = [comensales]
    filtro = ""
    if zona in ZONAS:
        filtro = " AND zona=%s"
        args.append(zona)
    return q(f"SELECT id, nombre, zona, plazas FROM mesas WHERE plazas >= %s{filtro} "
             f"ORDER BY plazas, id", tuple(args))


def mesa_ocupada(mesa_id: int, hora: datetime, cfg: dict, excluir: int | None = None) -> bool:
    """¿Choca con otra reserva viva de esa mesa?

    Dos reservas chocan si sus ventanas de `duracion_min` se pisan, que es lo mismo que decir
    que la diferencia entre sus horas es menor que la duración.
    """
    dur = cfg["duracion_min"]
    args: list = [mesa_id, hora, dur, hora, dur]
    filtro = ""
    if excluir:
        filtro = " AND id<>%s"
        args.append(excluir)
    fila = q1(f"""SELECT COUNT(*) n FROM reservas
                  WHERE mesa_id=%s AND estado IN ('pendiente','confirmada','sentada')
                    AND hora > %s - INTERVAL %s MINUTE
                    AND hora < %s + INTERVAL %s MINUTE{filtro}""", tuple(args))
    return bool(fila["n"])


def asignar_mesa(hora: datetime, comensales: int, zona: str | None, cfg: dict,
                 excluir: int | None = None) -> dict | None:
    for mesa in mesas_para(comensales, zona):
        if not mesa_ocupada(mesa["id"], hora, cfg, excluir):
            return mesa
    return None


def huecos(dia: datetime, comensales: int, zona: str | None, cfg: dict,
           ahora: datetime | None = None) -> list[dict]:
    """Franjas del día en las que queda alguna mesa para ese grupo."""
    ahora = ahora or datetime.now()
    minimo = ahora + timedelta(minutes=cfg["antelacion_min"])
    salida = []
    for franja in franjas_del_dia(dia, cfg):
        if franja < minimo:
            continue
        mesa = asignar_mesa(franja, comensales, zona, cfg)
        if mesa:
            salida.append({"hora": franja, "mesa": mesa["nombre"], "mesa_id": mesa["id"],
                           "zona": mesa["zona"]})
    return salida


# ─────────────── Comprobaciones al crear ───────────────
class NoSePuede(Exception):
    """Motivo en cristiano de por qué no se admite la reserva, y el código HTTP que le toca."""

    def __init__(self, codigo: int, motivo: str):
        super().__init__(motivo)
        self.codigo = codigo
        self.motivo = motivo


def revisar(hora: datetime, comensales: int, zona: str | None, cfg: dict,
            ahora: datetime | None = None, excluir: int | None = None,
            saltar_antelacion: bool = False, mesa_id: int | None = None) -> dict:
    """Devuelve la mesa asignada o explota con el motivo. `saltar_antelacion` es para el
    camarero que coge el teléfono con el cliente ya en la puerta.

    `mesa_id` es para la sala, cuando pulsa un hueco del planning: quiere ESA mesa, no la que
    toque. Pasa las mismas reglas que un cambio de mesa (que quepan y que no se pise con otra
    reserva); lo que no hace es buscar otra si esa no vale, porque no es lo que se ha pedido."""
    ahora = ahora or datetime.now()
    if not cfg["activas"]:
        raise NoSePuede(409, "Ahora mismo no se admiten reservas")
    if zona and zona not in ZONAS:
        raise NoSePuede(422, "Esa zona no existe")
    if not saltar_antelacion and hora < ahora + timedelta(minutes=cfg["antelacion_min"]):
        raise NoSePuede(422, f"Las reservas se piden con {cfg['antelacion_min']} minutos "
                             f"de antelación como mínimo")
    if hora > ahora + timedelta(days=cfg["max_dias"]):
        raise NoSePuede(422, f"No se reserva con más de {cfg['max_dias']} días de antelación")
    if not en_horario(hora, cfg):
        raise NoSePuede(422, f"A esa hora no hay servicio (horario: {cfg['horario']})")
    if mesa_id is not None:
        mesa = q1("SELECT id, nombre, zona, plazas FROM mesas WHERE id=%s", (mesa_id,))
        if not mesa:
            raise NoSePuede(404, "Esa mesa no existe")
        if mesa["plazas"] < comensales:
            raise NoSePuede(409, f"En la {mesa['nombre']} caben {mesa['plazas']}, "
                                 f"y son {comensales}")
        if mesa_ocupada(mesa["id"], hora, cfg, excluir):
            raise NoSePuede(409, f"La {mesa['nombre']} ya está reservada a esa hora")
        return mesa
    if not mesas_para(comensales, zona):
        cabe = q1("SELECT MAX(plazas) m FROM mesas")["m"] or 0
        raise NoSePuede(409, f"No hay ninguna mesa para {comensales}; la mayor es de {cabe}")
    mesa = asignar_mesa(hora, comensales, zona, cfg, excluir)
    if not mesa:
        raise NoSePuede(409, "No queda mesa libre a esa hora")
    return mesa


def nuevo_token() -> str:
    return secrets.token_hex(16)


# ─────────────── Consultas ───────────────
def lineas(reserva_id: int) -> list[dict]:
    return q("""SELECT rl.id, rl.producto_id, rl.cantidad, rl.notas,
                       p.nombre, p.precio_cent, p.disponible, p.estacion
                FROM reserva_lineas rl JOIN productos p ON p.id=rl.producto_id
                WHERE rl.reserva_id=%s ORDER BY rl.id""", (reserva_id,))


def completa(reserva_id: int) -> dict | None:
    r = q1("""SELECT r.*, m.nombre AS mesa FROM reservas r
              LEFT JOIN mesas m ON m.id=r.mesa_id WHERE r.id=%s""", (reserva_id,))
    if not r:
        return None
    r["lineas"] = lineas(reserva_id)
    r["total_cent"] = sum(l["cantidad"] * l["precio_cent"] for l in r["lineas"])
    return r


def por_token(token: str) -> dict | None:
    r = q1("SELECT id FROM reservas WHERE token=%s", (token,))
    return completa(r["id"]) if r else None


def agenda(dia: datetime) -> list[dict]:
    """Todas las reservas de un día, en orden de hora, con su pedido adelantado."""
    filas = q("""SELECT r.*, m.nombre AS mesa, e.nombre AS creada_por_nombre
                 FROM reservas r
                 LEFT JOIN mesas m ON m.id=r.mesa_id
                 LEFT JOIN empleados e ON e.id=r.creada_por
                 WHERE DATE(r.hora)=%s ORDER BY r.hora, r.id""", (dia.date(),))
    for f in filas:
        f["lineas"] = lineas(f["id"])
        f["total_cent"] = sum(l["cantidad"] * l["precio_cent"] for l in f["lineas"])
    return filas


def pendientes_de_soltar(cfg: dict, ahora: datetime | None = None) -> list[dict]:
    """Reservas cuyo pedido adelantado ya toca mandar a cocina.

    Se mira la hora menos el margen; las que se quedaron atrás (porque el servicio estuvo
    parado) entran también, que es mejor tarde que nunca, pero no las de ayer: si pasó más de
    una duración desde la hora, el cliente ya no está y sería tirar comida.
    """
    ahora = ahora or datetime.now()
    return q("""SELECT r.id FROM reservas r
                WHERE r.estado IN ('pendiente','confirmada')
                  AND r.soltada_en IS NULL
                  AND EXISTS (SELECT 1 FROM reserva_lineas rl WHERE rl.reserva_id=r.id)
                  AND r.hora <= %s + INTERVAL %s MINUTE
                  AND r.hora >= %s - INTERVAL %s MINUTE
                ORDER BY r.hora""",
             (ahora, cfg["margen_cocina_min"], ahora, cfg["duracion_min"]))
