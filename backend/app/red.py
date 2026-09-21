"""Política de red del servicio: quién puede hablar con él.

Vive aparte para que el redirector del puerto 8090 no tenga que cargar la aplicación
entera (ni la base de datos) solo para saber si un cliente es de casa.
"""
import os
from ipaddress import ip_address, ip_network

# Redes privadas (RFC 1918) más el bucle local. Se puede afinar por entorno:
#   KDS_REDES=192.168.1.0/24   → solo la red del local
REDES_PERMITIDAS = [
    ip_network(r.strip()) for r in
    os.getenv("KDS_REDES", "127.0.0.0/8,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1/128").split(",")
    if r.strip()
]


# Nombres (no IPs) que se aceptan igualmente. Vacío en producción; las pruebas ponen
# "testclient", que es el nombre con el que se presenta el cliente de pruebas de FastAPI.
HOSTS_PERMITIDOS = {h.strip() for h in os.getenv("KDS_HOSTS", "").split(",") if h.strip()}


def es_de_la_lan(host: str | None) -> bool:
    """True si la IP del cliente está en una de las redes permitidas.

    Se mira SIEMPRE la IP real de la conexión, nunca una cabecera tipo `X-Forwarded-For`:
    esa la escribe quien llama y se falsifica en un segundo. Si algún día hay un nginx
    delante, la comprobación se hace allí y aquí solo entra tráfico de localhost.
    """
    if not host:
        return False
    if host in HOSTS_PERMITIDOS:
        return True
    try:
        ip = ip_address(host)
    except ValueError:
        return False
    return any(ip in red for red in REDES_PERMITIDAS if ip.version == red.version)
