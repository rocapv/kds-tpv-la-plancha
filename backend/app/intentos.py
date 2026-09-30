"""Registro de entradas del personal: quién intenta entrar, desde dónde y cuántas veces.

`home.pr1.es` está abierto a internet y la puerta es un PIN de cuatro cifras. Esto no frena a
nadie —eso vendrá después—: sirve para que el encargado VEA qué está pasando antes de decidir cómo
frenarlo. Se apunta cada entrada, buena o mala, pero nunca lo que se tecleó (ver 24_intentos_login.sql).
"""
from ipaddress import ip_address

from .db import q, q1


def _dias_de_registro() -> int:
    fila = q1("SELECT valor FROM ajustes WHERE clave='intentos_dias'")
    try:
        return max(1, int(fila["valor"])) if fila else 30
    except ValueError:
        return 30


def apuntar(ip: str | None, via: str, ok: bool, empleado_id: int | None = None,
            agente: str | None = None) -> None:
    q("""INSERT INTO empleado_intentos (ip, via, ok, empleado_id, agente)
         VALUES (%s,%s,%s,%s,%s)""",
      (ip, via, ok, empleado_id, (agente or "")[:120] or None))
    q("DELETE FROM empleado_intentos WHERE cuando < NOW() - INTERVAL %s DAY",   # limpieza perezosa
      (_dias_de_registro(),))


def origen(ip: str | None) -> str:
    """«local» o «internet». Se mira la IP en sí, no `KDS_REDES`: en Raspa esa variable deja
    pasar a todo el mundo (0.0.0.0/0) y entonces cualquier IP parecería de casa."""
    if not ip:
        return "desconocido"
    try:
        dir_ = ip_address(ip)
    except ValueError:
        return "desconocido"
    return "local" if (dir_.is_private or dir_.is_loopback) else "internet"


def resumen(horas: int = 24) -> dict:
    """Lo que ve el encargado: una fila por IP con sus fallos, y los últimos intentos sueltos.

    Una IP que falla y después ENTRA se marca aparte: puede ser alguien del equipo que se
    equivocó de PIN, o alguien de fuera que lo acertó. Solo lo sabe quien conoce a su gente.
    """
    horas = max(1, min(int(horas), 24 * 30))
    por_ip = q("""SELECT ip,
                         SUM(NOT ok) AS fallos,
                         SUM(ok)     AS aciertos,
                         SUM(NOT ok AND via='pin')        AS fallos_pin,
                         SUM(NOT ok AND via='contrasena') AS fallos_contrasena,
                         MIN(cuando) AS primero,
                         MAX(cuando) AS ultimo,
                         MAX(CASE WHEN NOT ok THEN cuando END) AS ultimo_fallo,
                         MIN(CASE WHEN NOT ok THEN id END) AS primer_fallo_id
                  FROM empleado_intentos
                  WHERE cuando >= NOW() - INTERVAL %s HOUR
                  GROUP BY ip
                  HAVING fallos > 0
                  ORDER BY fallos DESC, ultimo DESC
                  LIMIT 100""", (horas,))
    for f in por_ip:
        for k in ("fallos", "aciertos", "fallos_pin", "fallos_contrasena"):
            f[k] = int(f[k] or 0)
        f["origen"] = origen(f["ip"])
        # Quién entró desde esa IP DESPUÉS de fallar: es la pregunta que importa. Se ordena por
        # id y no por hora, que va a segundos: un fallo y un acierto en el mismo segundo empatan.
        f["entraron_despues"] = [r["nombre"] for r in q(
            """SELECT DISTINCT e.nombre FROM empleado_intentos i
               JOIN empleados e ON e.id=i.empleado_id
               WHERE i.ok AND i.ip <=> %s AND i.id > %s""",
            (f["ip"], f.pop("primer_fallo_id")))]

    recientes = q("""SELECT i.cuando, i.ip, i.via, i.ok, i.empleado_id, e.nombre, i.agente
                     FROM empleado_intentos i LEFT JOIN empleados e ON e.id=i.empleado_id
                     WHERE i.cuando >= NOW() - INTERVAL %s HOUR AND NOT i.ok
                     ORDER BY i.id DESC LIMIT 50""", (horas,))
    for r in recientes:
        r["origen"] = origen(r["ip"])
        r["ok"] = bool(r["ok"])

    totales = q1("""SELECT COALESCE(SUM(NOT ok),0) AS fallos, COALESCE(SUM(ok),0) AS aciertos,
                           COUNT(DISTINCT CASE WHEN NOT ok THEN ip END) AS ips
                    FROM empleado_intentos WHERE cuando >= NOW() - INTERVAL %s HOUR""", (horas,))
    return {"horas": horas,
            "fallos": int(totales["fallos"]), "aciertos": int(totales["aciertos"]),
            "ips_con_fallos": int(totales["ips"]),
            "de_internet": sum(f["fallos"] for f in por_ip if f["origen"] == "internet"),
            "por_ip": por_ip, "recientes": recientes,
            "dias_de_registro": _dias_de_registro()}
