"""La interfaz: una caja de texto y un botón.

Servidor de la biblioteca estándar a propósito. Esto lo usa una persona desde su
propio ordenador; meter FastAPI, uvicorn y sus veinte dependencias para servir
cuatro rutas es pagar mantenimiento por nada. Sin dependencias nuevas, el
estudio arranca con el intérprete que ya hay.

Escucha solo en 127.0.0.1. La web del estudio deja disparar trabajos que graban
pantallas del KDS con PIN de encargado: eso no sale de esta máquina.
"""
from __future__ import annotations

import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import biblia as B
from . import comfy as C
from . import elenco as E
from . import guion as Gu
from . import produccion as Pr
from . import voz as V

DIR_WEB = B.RAIZ / "web"
PUERTO = 8099


# Preguntar por la salud cuesta un par de segundos: hay un SSH a Raspa para saber
# si Piper contesta y una llamada al LLM. Se guarda unos segundos para que la web
# pueda refrescarse a menudo sin hacer un SSH cada vez.
_ultima_salud: tuple[float, dict] | None = None
VIGENCIA_SALUD = 12.0


def _salud(forzar: bool = False) -> dict:
    global _ultima_salud
    if not forzar and _ultima_salud and (time.time() - _ultima_salud[0]) < VIGENCIA_SALUD:
        return _ultima_salud[1]

    d: dict = {"comfy": False, "vram_libre": 0, "vram_total": 0, "llm": False,
               "piper": False, "casting_falta": [], "camaras": len(B.CAMARAS)}
    d["comfy"] = C.encendido()
    if d["comfy"]:
        try:
            d["vram_libre"], d["vram_total"] = C.vram_libre()
        except Exception:
            pass
    d["llm"] = Gu.hay_llm()
    d["piper"] = V.disponible()
    d["casting_falta"] = E.falta_casting()
    try:
        bib = B.cargar()
        d["local"] = bib.local.get("local_nombre") or "Cantina Vesta-9"
        d["mesas"] = len(bib.mesas)
        d["platos"] = len(bib.platos)
    except Exception as e:
        d["biblia_error"] = str(e)
    _ultima_salud = (time.time(), d)
    return d


class Manejador(BaseHTTPRequestHandler):
    server_version = "EstudioKDS"

    def log_message(self, formato, *args):        # silencio: ya hay traza en trabajos/
        pass

    # ── utilidades ──────────────────────────────────────────────────────
    def _json(self, datos, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _fichero(self, ruta: Path, raiz: Path) -> None:
        try:
            ruta = ruta.resolve()
            raiz = raiz.resolve()
            ruta.relative_to(raiz)          # que nadie salga de la carpeta con ../
        except (ValueError, OSError):
            self._json({"error": "fuera de sitio"}, 403)
            return
        if not ruta.exists() or not ruta.is_file():
            self._json({"error": "no está"}, 404)
            return
        tipo = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        datos = ruta.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Accept-Ranges", "none")
        self.end_headers()
        self.wfile.write(datos)

    def _cuerpo(self) -> dict:
        largo = int(self.headers.get("Content-Length") or 0)
        if not largo:
            return {}
        try:
            return json.loads(self.rfile.read(largo).decode("utf-8"))
        except Exception:
            return {}

    # ── rutas ───────────────────────────────────────────────────────────
    def do_GET(self):
        ruta = unquote(urlparse(self.path).path)

        if ruta in ("/", "/index.html"):
            self._fichero(DIR_WEB / "estudio.html", DIR_WEB)
        elif ruta.startswith("/web/"):
            self._fichero(DIR_WEB / ruta[5:], DIR_WEB)
        elif ruta == "/api/salud":
            self._json(_salud())
        elif ruta == "/api/catalogo":
            self._json({
                "camaras": [{"clave": c.clave, "nombre": c.nombre, "nota": c.nota}
                            for c in B.CAMARAS.values()],
                "elenco": [{"clave": p.clave, "nombre": p.nombre, "papel": p.papel,
                            "retrato": E.ruta_de(p.clave).exists()}
                           for p in B.ELENCO.values()],
                "pantallas": [{"clave": k, "nombre": v[2]} for k, v in B.PANTALLAS.items()],
            })
        elif ruta == "/api/trabajos":
            self._json(Pr.Trabajo.listar())
        elif ruta.startswith("/api/trabajo/"):
            e = Pr.Trabajo.cargar(ruta.rsplit("/", 1)[-1])
            self._json(e or {"error": "no existe"}, 200 if e else 404)
        elif ruta.startswith("/salidas/"):
            self._fichero(Pr.DIR_SALIDAS / ruta[len("/salidas/"):], Pr.DIR_SALIDAS)
        elif ruta.startswith("/biblia/"):
            self._fichero(B.DIR_BIBLIA / ruta[len("/biblia/"):], B.DIR_BIBLIA)
        else:
            self._json({"error": "no hay nada aquí"}, 404)

    def do_POST(self):
        ruta = unquote(urlparse(self.path).path)
        datos = self._cuerpo()

        if ruta == "/api/producir":
            prompt = (datos.get("prompt") or "").strip()
            if not prompt:
                self._json({"error": "hace falta un prompt"}, 400)
                return
            ident = Pr.lanzar(prompt,
                              usar_llm=bool(datos.get("usar_llm", True)),
                              con_voz=bool(datos.get("con_voz", True)),
                              solo_guion=bool(datos.get("solo_guion", False)))
            self._json({"id": ident})

        elif ruta == "/api/casting":
            def tarea():
                E.casting(rehacer=bool(datos.get("rehacer", False)))
            threading.Thread(target=tarea, daemon=True).start()
            self._json({"lanzado": True, "faltan": E.falta_casting()})

        elif ruta == "/api/biblia/actualizar":
            try:
                bib = B.descargar()
                from . import geometria as G
                G.generar_controles(bib)
                self._json({"ok": True, "mesas": len(bib.mesas), "platos": len(bib.platos)})
            except Exception as e:
                self._json({"error": str(e)}, 500)

        else:
            self._json({"error": "no hay nada aquí"}, 404)


def servir(puerto: int = PUERTO) -> None:
    Pr.DIR_TRABAJOS.mkdir(parents=True, exist_ok=True)
    Pr.DIR_SALIDAS.mkdir(parents=True, exist_ok=True)
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    print(f"Estudio del KDS en http://127.0.0.1:{puerto}")
    salud = _salud()
    print(f"  ComfyUI: {'sí' if salud['comfy'] else 'NO (lánzalo con Kinemato\\run.bat)'}"
          f" | VRAM libre: {salud['vram_libre']} MiB")
    print(f"  Guionista: {'modelo de lenguaje' if salud['llm'] else 'plantillas (sin LLM)'}"
          f" | Voz: {'Piper en Raspa' if salud['piper'] else 'no disponible'}")
    if salud["casting_falta"]:
        print(f"  Falta el retrato de: {', '.join(salud['casting_falta'])}")
    servidor.serve_forever()
