#!/usr/bin/env python3
"""Servidor de la presentación del Reto 1 para la red local: todos los clientes ven siempre la misma diapositiva.

Cada equipo elige su vista: las diapositivas (proyector) o el guion del orador, con la diapositiva en pequeño.
Cuando cualquiera avanza o retrocede, el servidor avisa a todos con Server-Sent Events. Solo biblioteca estándar.

Uso: python3 servidor.py [--puerto 8000]   y abrir en cada equipo de la LAN la dirección que imprime.
Rutas: /eventos (SSE con el estado), /estado (JSON), POST /ir {"i": n} (cambia de diapositiva, n desde 0).
"""
import argparse, functools, json, select, socket, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

AQUI = Path(__file__).resolve().parent
VISTAS = ("diapositiva", "guion")
estado = {"i": 0, "v": 0, "clientes": {v: 0 for v in VISTAS}}
cambio = threading.Condition()


def hora():
    return time.strftime("%H:%M:%S")


def publica(**cambios):
    """Aplica los cambios al estado y despierta a todas las conexiones de /eventos."""
    with cambio:
        for k, v in cambios.items():
            estado[k] = v
        estado["v"] += 1
        cambio.notify_all()


def cuenta(vista, d):
    """Suma o resta un cliente conectado con esa vista y avisa a todos."""
    with cambio:
        estado["clientes"][vista] += d
        estado["v"] += 1
        cambio.notify_all()


class Manejador(SimpleHTTPRequestHandler):
    def log_message(self, *args):          # sin una línea por cada fichero servido
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/eventos":
            return self._eventos(parse_qs(url.query).get("vista", ["diapositiva"])[0])
        if url.path == "/estado":
            with cambio:
                return self._json({"i": estado["i"], "clientes": dict(estado["clientes"])})
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/ir":
            return self.send_error(404)
        try:
            n = int(json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["i"])
        except (ValueError, KeyError, TypeError):
            return self.send_error(400, "Se espera {\"i\": número de diapositiva}")
        if n < 0:
            return self.send_error(400, "La diapositiva no puede ser negativa")
        if n != estado["i"]:
            publica(i=n)
            print(f"{hora()}  {self.client_address[0]:<15} → diapositiva {n + 1}", flush=True)
        self._json({"i": n})

    def _cerrada(self):
        """El navegador no envía nada por /eventos: si el socket se puede leer, es que ha cerrado la conexión."""
        try:
            legible, _, _ = select.select([self.connection], [], [], 0)
            return bool(legible) and not self.connection.recv(1, socket.MSG_PEEK)
        except OSError:
            return True

    def _eventos(self, vista):
        vista = vista if vista in VISTAS else "diapositiva"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        cuenta(vista, +1)
        print(f"{hora()}  {self.client_address[0]:<15} se conecta ({vista})", flush=True)
        visto, ultimo = -1, 0.0
        try:
            while not self._cerrada():
                with cambio:
                    cambio.wait_for(lambda: estado["v"] != visto, timeout=1)
                    foto = {"i": estado["i"], "clientes": dict(estado["clientes"])}
                    nueva, visto = estado["v"] != visto, estado["v"]
                # cada 15 s sin cambios, un comentario mantiene viva la conexión a través de routers y proxies
                if nueva or time.monotonic() - ultimo > 15:
                    self.wfile.write(f"data: {json.dumps(foto)}\n\n".encode() if nueva else b": sigo\n\n")
                    self.wfile.flush()
                    ultimo = time.monotonic()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            cuenta(vista, -1)
            print(f"{hora()}  {self.client_address[0]:<15} se desconecta ({vista})", flush=True)


def direcciones():
    """IP de este equipo en la LAN (la de la ruta por defecto; no envía nada) y las demás que tenga."""
    ips = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips += [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if ip not in ips]
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith("127.")] or ["127.0.0.1"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--puerto", type=int, default=8000)
    args = ap.parse_args()
    servidor = ThreadingHTTPServer(("0.0.0.0", args.puerto), functools.partial(Manejador, directory=str(AQUI)))
    servidor.daemon_threads = True
    print(f"Presentación del Reto 1 · ServiPass · puerto {args.puerto}")
    ip, *otras = direcciones()
    print(f"  Elegir vista:  http://{ip}:{args.puerto}/")
    print(f"  Diapositivas:  http://{ip}:{args.puerto}/presentacion.html")
    print(f"  Guion:         http://{ip}:{args.puerto}/presentacion.html?vista=guion")
    if otras:
        print("  Si esa red no es la del aula, probar con:", ", ".join(f"http://{o}:{args.puerto}/" for o in otras))
    print("Ctrl+C para parar.", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nParado.")
