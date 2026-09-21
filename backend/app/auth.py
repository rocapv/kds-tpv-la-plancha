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


def usuario(authorization: str | None = Header(None),
            x_token: str | None = Header(None)) -> dict:
    """Devuelve el empleado de la sesión o corta con 401."""
    token = _token_de(authorization, x_token)
    if not token:
        raise HTTPException(401, "Hace falta iniciar sesión")
    s = q1("""SELECT s.token, s.caduca_en, e.id, e.nombre, e.rol
              FROM sesiones s JOIN empleados e ON e.id=s.empleado_id
              WHERE s.token=%s AND e.activo""", (token,))
    if not s:
        raise HTTPException(401, "Sesión no válida")
    if s["caduca_en"] < datetime.now():
        cerrar_sesion(token)
        raise HTTPException(401, "La sesión ha caducado")
    q("UPDATE sesiones SET ultimo_uso=NOW() WHERE token=%s", (token,))
    return s


def exige(*roles: str):
    """Dependencia: exige sesión y, si se indican roles, uno de ellos."""
    def guardia(u: dict = Depends(usuario)) -> dict:
        if roles and u["rol"] not in roles:
            raise HTTPException(403, f"Necesitas rol {' o '.join(roles)}; el tuyo es {u['rol']}")
        return u
    return guardia


def usuario_de_token(token: str | None) -> dict | None:
    """Validación suelta para el WebSocket, que no pasa por las dependencias HTTP."""
    if not token:
        return None
    return q1("""SELECT e.id, e.nombre, e.rol FROM sesiones s JOIN empleados e ON e.id=s.empleado_id
                 WHERE s.token=%s AND e.activo AND s.caduca_en > NOW()""", (token,))
