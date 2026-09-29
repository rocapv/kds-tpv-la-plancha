"""Cuentas de cliente: correo y contraseña, y un token que dura hasta que el cliente sale.

Separado del personal a conciencia. Un empleado entra con PIN o con contraseña y su token abre
pantallas de trabajo; un cliente entra con su correo y el suyo **no abre nada de dentro**: solo
su perfil, sus pedidos y sus facturas. Son dos puertas distintas al mismo edificio, y la del
cliente da a la calle (`home.pr1.es` está abierto a internet), así que lleva freno de intentos.

Lo que se guarda del cliente es lo mínimo: correo, contraseña cifrada y, si él quiere, nombre,
teléfono y datos fiscales para la factura. Nada más. Un restaurante no necesita un fichero de
clientes, necesita poder emitir la factura que le pidan.
"""
import re
import secrets
from datetime import datetime

from fastapi import Header, HTTPException

from .auth import cifrar_clave, clave_correcta
from .db import conn, q, q1

CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
CAMPOS_PERFIL = ("nombre", "telefono", "nif", "razon_social", "direccion", "factura_auto")


def _ajuste(clave: str, por_defecto: str) -> str:
    fila = q1("SELECT valor FROM ajustes WHERE clave=%s", (clave,))
    return str(fila["valor"]) if fila else por_defecto


def registro_abierto() -> bool:
    return _ajuste("clientes_registro", "si").strip().lower() in ("si", "sí", "1", "true")


def _entero(clave: str, por_defecto: int) -> int:
    try:
        return int(_ajuste(clave, str(por_defecto)))
    except ValueError:
        return por_defecto


# ─────────────── Freno de intentos ───────────────
def frenado(email: str | None, ip: str | None) -> bool:
    """¿Demasiados fallos recientes desde este correo o esta IP?

    Se miran las dos cosas: el correo, para que no prueben mil contraseñas contra una cuenta; y
    la IP, para que no prueben una contraseña contra mil cuentas.
    """
    tope = _entero("cliente_intentos_max", 8)
    ventana = _entero("cliente_intentos_min", 15)
    fila = q1("""SELECT COUNT(*) n FROM cliente_intentos
                 WHERE cuando >= NOW() - INTERVAL %s MINUTE
                   AND ((%s IS NOT NULL AND email=%s) OR (%s IS NOT NULL AND ip=%s))""",
              (ventana, email, email, ip, ip))
    return fila["n"] >= tope


def apuntar_fallo(email: str | None, ip: str | None) -> None:
    q("INSERT INTO cliente_intentos (email, ip) VALUES (%s,%s)", (email, ip))
    q("DELETE FROM cliente_intentos WHERE cuando < NOW() - INTERVAL 1 DAY")   # limpieza perezosa


def limpiar_fallos(email: str) -> None:
    q("DELETE FROM cliente_intentos WHERE email=%s", (email,))


# ─────────────── Alta y entrada ───────────────
def normalizar(email: str) -> str:
    return email.strip().lower()


def validar(email: str, contrasena: str) -> None:
    if not CORREO.match(email):
        raise HTTPException(422, "Ese correo no tiene buena pinta")
    if len(contrasena) < 8:
        raise HTTPException(422, "La contraseña tiene que tener ocho caracteres por lo menos")


def crear(email: str, contrasena: str, nombre: str | None, agente: str | None) -> dict:
    email = normalizar(email)
    validar(email, contrasena)
    if q1("SELECT id FROM clientes WHERE email=%s", (email,)):
        raise HTTPException(409, "Ya hay una cuenta con ese correo")
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO clientes (email, contrasena, nombre) VALUES (%s,%s,%s)",
                    (email, cifrar_clave(contrasena), (nombre or "").strip() or None))
        cid = cur.lastrowid
    return abrir_sesion(cid, agente)


def entrar(email: str, contrasena: str, agente: str | None, ip: str | None) -> dict:
    email = normalizar(email)
    if frenado(email, ip):
        raise HTTPException(429, "Demasiados intentos; espera un rato antes de volver a probar")
    c = q1("SELECT id, contrasena, activo FROM clientes WHERE email=%s", (email,))
    if not c or not c["activo"] or not clave_correcta(contrasena, c["contrasena"]):
        apuntar_fallo(email, ip)
        # El mismo mensaje en los dos casos: decir «ese correo no existe» es decirle a quien
        # prueba cuáles sí existen.
        raise HTTPException(401, "Correo o contraseña que no cuadran")
    limpiar_fallos(email)
    return abrir_sesion(c["id"], agente)


def abrir_sesion(cliente_id: int, agente: str | None) -> dict:
    token = secrets.token_hex(32)
    q("""INSERT INTO cliente_sesiones (token, cliente_id, ultimo_uso, agente)
         VALUES (%s,%s,NOW(),%s)""", (token, cliente_id, (agente or "")[:120] or None))
    q("UPDATE clientes SET ultimo_acceso=NOW() WHERE id=%s", (cliente_id,))
    return {"token": token, **perfil(cliente_id)}


def salir(token: str) -> None:
    q("DELETE FROM cliente_sesiones WHERE token=%s", (token,))


def salir_de_todos(cliente_id: int) -> int:
    """Cerrar la sesión en todos los aparatos: lo que se pulsa cuando se pierde el móvil."""
    return len(q("SELECT token FROM cliente_sesiones WHERE cliente_id=%s", (cliente_id,))) and \
        q("DELETE FROM cliente_sesiones WHERE cliente_id=%s", (cliente_id,)) or 0


# ─────────────── Perfil ───────────────
def perfil(cliente_id: int) -> dict:
    c = q1("""SELECT id, email, nombre, telefono, nif, razon_social, direccion,
                     factura_auto, alta_en, ultimo_acceso
              FROM clientes WHERE id=%s""", (cliente_id,))
    if not c:
        raise HTTPException(404, "Esa cuenta ya no existe")
    c["factura_auto"] = bool(c["factura_auto"])
    return c


def guardar_perfil(cliente_id: int, cambios: dict) -> dict:
    campos, args = [], []
    for campo in CAMPOS_PERFIL:
        if campo in cambios:
            campos.append(f"{campo}=%s")
            valor = cambios[campo]
            args.append(valor.strip() or None if isinstance(valor, str) else valor)
    if campos:
        q(f"UPDATE clientes SET {', '.join(campos)} WHERE id=%s", (*args, cliente_id))
    return perfil(cliente_id)


def cambiar_contrasena(cliente_id: int, actual: str, nueva: str) -> None:
    c = q1("SELECT email, contrasena FROM clientes WHERE id=%s", (cliente_id,))
    if not c or not clave_correcta(actual, c["contrasena"]):
        raise HTTPException(401, "La contraseña de ahora no es esa")
    validar(c["email"], nueva)
    q("UPDATE clientes SET contrasena=%s WHERE id=%s", (cifrar_clave(nueva), cliente_id))


# ─────────────── Dependencia para los endpoints ───────────────
def de_token(token: str | None) -> dict | None:
    if not token:
        return None
    s = q1("""SELECT s.token, c.id FROM cliente_sesiones s
              JOIN clientes c ON c.id=s.cliente_id
              WHERE s.token=%s AND c.activo""", (token,))
    if not s:
        return None
    q("UPDATE cliente_sesiones SET ultimo_uso=NOW() WHERE token=%s", (token,))
    return perfil(s["id"])


def cliente(authorization: str | None = Header(None)) -> dict:
    """Exige cuenta de cliente. Devuelve su perfil, nunca su contraseña."""
    token = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
    yo = de_token(token)
    if not yo:
        raise HTTPException(401, "Entra con tu cuenta")
    yo["token"] = token
    return yo


def cliente_opcional(authorization: str | None = Header(None)) -> dict | None:
    """Para lo que funciona con cuenta y sin ella: pedir desde la mesa, por ejemplo."""
    token = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
    return de_token(token)
