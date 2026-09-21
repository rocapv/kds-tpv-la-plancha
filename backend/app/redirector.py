"""Servidor mínimo en el puerto 8090: manda a todo el mundo al HTTPS.

Así una pantalla vieja con la dirección antigua guardada acaba igualmente en TLS,
y nadie sigue tecleando su PIN sobre HTTP.
"""
import os

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from .red import es_de_la_lan

PUERTO_TLS = os.getenv("KDS_SOLO_REDIRECCION", "8443")
app = FastAPI(title="KDS + TPV · redirección a HTTPS")




@app.middleware("http")
async def solo_lan(request: Request, call_next):
    if not es_de_la_lan(request.client.host if request.client else None):
        return PlainTextResponse("Este servicio solo atiende a la red local", status_code=403)
    return await call_next(request)


@app.get("/{ruta:path}")
def a_https(ruta: str, request: Request):
    destino = f"https://{request.url.hostname}:{PUERTO_TLS}/{ruta}"
    if request.url.query:
        destino += "?" + request.url.query
    return RedirectResponse(destino, status_code=301)
