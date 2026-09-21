"""Sesiones con token y control de roles.

El PIN solo viaja en el momento de entrar; a partir de ahí cada petición lleva
`Authorization: Bearer <token>`. El token se guarda en la BD, así que un reinicio
del servicio no echa a nadie a media comanda.

Roles:
  camarero  → sala: carta, mesas, pedidos, cobros y documentos.
  cocina    → pantallas KDS y avance de comandas.
  encargado → todo lo anterior más usuarios, carta, ajustes e informes.
"""
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException

from .db import conn, q, q1

DURACION_POR_DEFECTO_H = 12


def _horas_sesion() -> int:
    fila = q1("SELECT valor FROM ajustes WHERE clave='sesion_horas'")
    try:
        return max(1, int(fila["valor"])) if fila else DURACION_POR_DEFECTO_H
    except ValueError:
        return DURACION_POR_DEFECTO_H


def abrir_sesion(pin: str, agente: str | None) -> dict:
    e = q1("SELECT id, nombre, rol FROM empleados WHERE pin=%s AND activo", (pin,))
    if not e:
        raise HTTPException(401, "PIN incorrecto")
    token = secrets.token_urlsafe(32)
    caduca = datetime.now() + timedelta(hours=_horas_sesion())
    q("""INSERT INTO sesiones (token, empleado_id, caduca_en, agente) VALUES (%s,%s,%s,%s)""",
      (token, e["id"], caduca, (agente or "")[:120] or None))
    q("DELETE FROM sesiones WHERE caduca_en < NOW()")          # limpieza perezosa
    return {"token": token, "caduca_en": caduca, **e}


def cerrar_sesion(token: str) -> None:
    q("DELETE FROM sesiones WHERE token=%s", (token,))


def _token_de(cabecera: str | None, alternativa: str | None) -> str | None:
    if cabecera and cabecera.lower().startswith("bearer "):
        return cabecera[7:].strip()
    return alternativa


def puesto_de(empleado: dict) -> dict | None:
    """El puesto donde está el empleado, con la pantalla y el rol que le toca allí."""
    if not empleado.get("puesto"):
        return None
    return q1("SELECT * FROM puestos WHERE clave=%s", (empleado["puesto"],))


def guis_de(rol_operativo: str | None, rol_real: str, gui: str | None) -> list[str]:
    """Pantallas que puede abrir alguien con ese puesto. El encargado conserva las de gestión
    aunque esté fregando platos: si no, se quedaría sin poder devolverse a la oficina."""
    permitidas = {"index.html"}
    if rol_operativo == "camarero":
        permitidas |= {"tpv.html", "facturas.html"}
    elif rol_operativo == "cocina":
        permitidas |= {"kds.html", "recogida.html"}
    if rol_real == "encargado":
        permitidas |= {"usuarios.html", "carta.html", "ajustes.html", "informe.html",
                       "arqueo.html", "facturas.html", "tpv.html", "kds.html", "recogida.html"}
    if gui:
        permitidas.add(gui.split("?")[0])
    return sorted(permitidas)


def usuario(authorization: str | None = Header(None),
            x_token: str | None = Header(None)) -> dict:
    """Devuelve el empleado de la sesión o corta con 401."""
    token = _token_de(authorization, x_token)
    if not token:
        raise HTTPException(401, "Hace falta iniciar sesión")
    s = q1("""SELECT s.token, s.caduca_en, e.id, e.nombre, e.rol, e.puesto
              FROM sesiones s JOIN empleados e ON e.id=s.empleado_id
              WHERE s.token=%s AND e.activo""", (token,))
    if not s:
        raise HTTPException(401, "Sesión no válida")
    if s["caduca_en"] < datetime.now():
        cerrar_sesion(token)
        raise HTTPException(401, "La sesión ha caducado")
    q("UPDATE sesiones SET ultimo_uso=NOW() WHERE token=%s", (token,))
    # El puesto del plano manda sobre el rol para todo lo operativo (ver 08_puestos.sql).
    p = puesto_de(s)
    s["puesto_nombre"] = p["nombre"] if p else None
    # Un puesto sin rol propio pero CON pantalla (la oficina) no quita nada: se trabaja con el
    # rol de siempre. Solo deja fuera de servicio el puesto que no tiene ni pantalla.
    if not p:
        s["rol_operativo"] = s["rol"]
    elif p["rol_operativo"]:
        s["rol_operativo"] = p["rol_operativo"]
    else:
        s["rol_operativo"] = s["rol"] if p["gui"] else None
    s["gui"] = (p["gui"] if p else None) or "index.html"
    s["guis"] = guis_de(s["rol_operativo"], s["rol"], s["gui"])
    return s


def exige(*roles: str):
    """Dependencia: exige sesión y, si se indican roles, uno de ellos.

    Dos varas de medir, a propósito:
      · gestión (`exige("encargado")` a secas) mira el rol REAL, para que el encargado no se
        quede fuera de la administración por haberse puesto en la plancha;
      · lo operativo mira el rol del PUESTO, que es lo que se ve en el plano.
    """
    def guardia(u: dict = Depends(usuario)) -> dict:
        if not roles:
            return u
        if tuple(roles) == ("encargado",):
            if u["rol"] != "encargado":
                raise HTTPException(403, f"Necesitas rol encargado; el tuyo es {u['rol']}")
            return u
        if u["rol_operativo"] in roles:
            return u
        if u["rol_operativo"] is None:
            raise HTTPException(403, f"{u['nombre']} está fuera de servicio"
                                     f"{' en ' + u['puesto_nombre'] if u['puesto_nombre'] else ''}:"
                                     " el encargado tiene que ponerte en un puesto del plano")
        raise HTTPException(403, f"Desde {u['puesto_nombre'] or 'tu puesto'} trabajas como "
                                 f"{u['rol_operativo']}, y esto es para {' o '.join(roles)}")
    return guardia


def usuario_de_token(token: str | None) -> dict | None:
    """Validación suelta para el WebSocket, que no pasa por las dependencias HTTP."""
    if not token:
        return None
    return q1("""SELECT e.id, e.nombre, e.rol, e.puesto FROM sesiones s JOIN empleados e ON e.id=s.empleado_id
                 WHERE s.token=%s AND e.activo AND s.caduca_en > NOW()""", (token,))
