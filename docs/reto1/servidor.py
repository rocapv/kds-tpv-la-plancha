#!/usr/bin/env python3
"""Servidor de la presentación del Reto 1 para la red local: todos los equipos van siempre a la vez.

Cuatro vistas: «presentación» (la pizarra, la principal), «público» (los móviles de la clase: siguen a la
presentación y votan en el cuestionario), «PC» (el guion del orador, con edición) y «móvil» (el mando, con las
notas rápidas). La diapositiva, el cronómetro, las animaciones, el cuestionario y los laboratorios son globales:
los mueve cualquier control y cambian en todos. Las tres vistas de control piden un PIN; el público, no.
Los laboratorios se ejecutan solo en la pizarra principal, y los demás reciben un espejo de lo que pasa en ella.
Solo biblioteca estándar.

Uso: python3 servidor.py [--puerto 8000] [--pin 1234 | --nuevo-pin] [--desde-cero]   y abrir la dirección que imprime.
El PIN, las sesiones abiertas y el estado se guardan en sesion_servidor.json: reiniciar el servidor no echa a
nadie y la presentación sigue en la misma diapositiva, con el cronómetro y los votos como estaban.
Los cambios del guion hechos desde el PC se guardan en guion_vivo.json, junto a este fichero.
"""
import argparse, functools, json, os, queue, re, secrets, select, socket, subprocess, threading, time, uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

AQUI = Path(__file__).resolve().parent
SESION, GUION_VIVO = AQUI / "sesion_servidor.json", AQUI / "guion_vivo.json"
VISTAS = ("presentacion", "publico", "pc", "mando")
CONTROL = ("presentacion", "pc", "mando")
PREGUNTAS, OPCIONES = 5, 4                   # PREGUNTAS = número de preguntas de PREG en presentacion.js
MAX_CUERPO = 2_000_000                       # una foto de laboratorio cabe de sobra

cerrojo = threading.RLock()
estado = {"i": 0, "mov": None, "crono": {"corre": False, "acum": 0.0, "desde": 0.0},
          "quiz": {"ronda": 1, "q": 0, "fase": "espera", "votos": [{} for _ in range(PREGUNTAS)]}}
suscritos = {}                               # id de conexión -> {"cola", "vista", "desde"}
sesion = {"pin": None, "tokens": []}
guion_vivo = {}
fallos = {}                                  # ip -> [intentos fallidos, bloqueado hasta]
ultimo_pedido = {}                           # laboratorio -> momento de la última petición de foto
pedidos_en_cola = set()                      # laboratorios con una petición de foto aplazada
publico_url = ""
VENTANA = 600                                # un equipo desconectado se sigue mostrando 10 minutos
vistos = {}                                  # (ip, vista) -> {"ip", "vista", "mac", "visto", "conectados"}
macs = {}                                    # ip -> (mac, cuándo se miró)


def hora():
    return time.strftime("%H:%M:%S")


def ahora_ms():
    return time.time() * 1000


def guarda_json(ruta, datos):
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ruta)


def principal():
    """La pizarra principal es la primera vista de presentación que se conectó y sigue conectada."""
    with cerrojo:
        pres = [(s["desde"], k) for k, s in suscritos.items() if s["vista"] == "presentacion"]
    return min(pres)[1] if pres else None


def foto_estado():
    with cerrojo:
        q = estado["quiz"]
        cuentas = {v: 0 for v in VISTAS}
        for s in suscritos.values():
            cuentas[s["vista"]] += 1
        return {"i": estado["i"], "mov": estado["mov"], "crono": dict(estado["crono"]), "ahora": ahora_ms(),
                "quiz": {"ronda": q["ronda"], "q": q["q"], "fase": q["fase"],
                         "recuentos": [[sum(1 for o in v.values() if o == k) for k in range(OPCIONES)] for v in q["votos"]]},
                "clientes": cuentas, "principal": principal(), "publico_url": publico_url}


def emite(evento, datos, a=None):
    """Mete un evento en la cola de cada conexión (o de una sola)."""
    msg = f"event: {evento}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n".encode()
    with cerrojo:
        for k, s in suscritos.items():
            if a is None or k == a:
                s["cola"].put(msg)


def guarda_sesion():
    """PIN, sesiones y estado (diapositiva, cronómetro, animaciones y votos): un reinicio continúa donde iba."""
    with cerrojo:
        guarda_json(SESION, {**sesion, "estado": estado})


def emite_estado(cambia=True):
    if cambia:
        guarda_sesion()
    emite("estado", foto_estado())
    emite_control("equipos", {"lista": lista_equipos(), "ahora": ahora_ms()})


def emite_control(evento, datos):
    """Como emite(), pero solo a las vistas con PIN: las MAC y las IP no llegan a los móviles del público."""
    msg = f"event: {evento}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n".encode()
    with cerrojo:
        for s in suscritos.values():
            if s["vista"] in CONTROL:
                s["cola"].put(msg)


def mac_de(ip):
    """MAC de un equipo de la LAN, sacada de la tabla ARP de este servidor (el navegador no puede darla)."""
    if ip in macs and macs[ip][1] > time.time() - 300:
        return macs[ip][0]
    mac = None
    if ip.startswith("127.") or ip == "::1" or ip in direcciones():
        n = uuid.getnode()
        mac = ":".join(f"{(n >> d) & 0xff:02x}" for d in range(40, -1, -8)) + " (el propio servidor)"
    else:
        try:                                 # Linux (Raspa)
            for linea in Path("/proc/net/arp").read_text().splitlines()[1:]:
                c = linea.split()
                if c and c[0] == ip and c[3] != "00:00:00:00:00:00":
                    mac = c[3]
        except OSError:                      # Windows y macOS
            try:
                salida = subprocess.run(["arp", "-a", ip], capture_output=True, text=True, timeout=3).stdout
                m = re.search(r"(?:[0-9a-fA-F]{1,2}[:-]){5}[0-9a-fA-F]{1,2}", salida)
                mac = m.group(0).replace("-", ":").lower() if m else None
            except (OSError, subprocess.SubprocessError):
                pass
    macs[ip] = (mac or "desconocida", time.time())
    return macs[ip][0]


def lista_equipos():
    """Equipos conectados y los que se fueron hace menos de 10 minutos, con la hora a la que se vieron."""
    ahora = time.time()
    with cerrojo:
        for k in [k for k, e in vistos.items() if not e["conectados"] and ahora - e["visto"] > VENTANA]:
            del vistos[k]
        return sorted(({"vista": e["vista"], "ip": e["ip"], "mac": e["mac"], "conectado": e["conectados"] > 0,
                        "visto": e["visto"] * 1000} for e in vistos.values()), key=lambda e: (not e["conectado"], e["ip"]))


def pide_foto(lab):
    with cerrojo:
        pedidos_en_cola.discard(lab)
        ultimo_pedido[lab] = time.time()
        p = principal()
    if p:
        emite("lab_pedir", {"lab": lab}, a=p)
    return bool(p)


class Manejador(SimpleHTTPRequestHandler):
    def log_message(self, *args):          # sin una línea por cada fichero servido
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _token_valido(self, token=None):
        token = token or self.headers.get("X-Token", "")
        return bool(token) and token in sesion["tokens"]

    def _cuerpo(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_CUERPO:
            raise ValueError("demasiado grande")
        return json.loads(self.rfile.read(n) or b"{}")

    # ---------- GET ----------
    def do_GET(self):
        url = urlsplit(self.path)
        q = parse_qs(url.query)
        if url.path == "/eventos":
            return self._eventos(q.get("vista", ["publico"])[0], q.get("token", [""])[0])
        if url.path == "/estado":
            return self._json(foto_estado())
        if url.path == "/guion":
            with cerrojo:
                return self._json(guion_vivo)
        if url.path == "/token":
            return self._json({"ok": self._token_valido()}, 200 if self._token_valido() else 401)
        if url.path in ("/p", "/publico"):
            self.send_response(302)
            self.send_header("Location", "/presentacion.html?vista=publico")
            return self.end_headers()
        return super().do_GET()

    def translate_path(self, path):
        """El fichero con el PIN y las sesiones no se sirve nunca, se pida como se pida."""
        ruta = super().translate_path(path)
        if Path(ruta).name in (SESION.name, SESION.with_suffix(".tmp").name):
            return str(AQUI / "__no_existe__")
        return ruta

    # ---------- POST ----------
    def do_POST(self):
        ruta = urlsplit(self.path).path
        try:
            d = self._cuerpo()
        except ValueError:
            return self.send_error(400, "JSON no válido")
        if ruta == "/entrar":
            return self._entrar(d)
        if ruta == "/votar":
            return self._votar(d)
        if ruta == "/lab/pedir":
            return self._lab_pedir(d)
        if not self._token_valido():
            return self.send_error(401, "Hace falta el PIN")
        acciones = {"/ir": self._ir, "/mov": self._mov, "/crono": self._crono, "/quiz": self._quiz,
                    "/guion": self._guion, "/lab/accion": self._lab_accion, "/lab/parche": self._lab_reenvia,
                    "/lab/foto": self._lab_reenvia}
        if ruta not in acciones:
            return self.send_error(404)
        try:
            return acciones[ruta](d, ruta)
        except (KeyError, TypeError, ValueError):
            return self.send_error(400, "Petición mal formada")

    def _entrar(self, d):
        ip = self.client_address[0]
        with cerrojo:
            n, hasta = fallos.get(ip, [0, 0])
            if hasta > time.time():
                return self._json({"espera": int(hasta - time.time()) + 1}, 429)
            if str(d.get("pin", "")) != sesion["pin"]:
                n += 1
                fallos[ip] = [0, time.time() + 60] if n >= 5 else [n, 0]
                print(f"{hora()}  {ip:<15} PIN incorrecto ({n})", flush=True)
                return self._json({"intentos": max(0, 5 - n)}, 403)
            fallos.pop(ip, None)
            token = secrets.token_urlsafe(16)
            sesion["tokens"].append(token)
            sesion["tokens"] = sesion["tokens"][-200:]
            guarda_sesion()
        print(f"{hora()}  {ip:<15} entra con PIN", flush=True)
        return self._json({"token": token})

    def _ir(self, d, _):
        n = int(d["i"])
        if not 0 <= n < 500:
            raise ValueError
        with cerrojo:
            cambia = n != estado["i"]
            estado["i"] = n
        if cambia:
            emite_estado()
            print(f"{hora()}  {self.client_address[0]:<15} → diapositiva {n + 1}", flush=True)
        return self._json({"i": n})

    def _mov(self, d, _):
        if d["mov"] not in ("on", "off"):
            raise ValueError
        with cerrojo:
            estado["mov"] = d["mov"]
        emite_estado()
        return self._json({"mov": d["mov"]})

    def _crono(self, d, _):
        with cerrojo:
            c, t = estado["crono"], ahora_ms()
            if d["accion"] == "alterna":
                if c["corre"]:
                    c["acum"] += (t - c["desde"]) / 1000
                    c["corre"] = False
                else:
                    c["desde"], c["corre"] = t, True
            elif d["accion"] == "reinicia":
                c["acum"], c["desde"] = 0.0, t
            else:
                raise ValueError
        emite_estado()
        return self._json(estado["crono"])

    def _quiz(self, d, _):
        with cerrojo:
            q, a = estado["quiz"], d["accion"]
            if a == "abrir" and q["fase"] == "espera":
                q["fase"] = "votando"
            elif a == "cerrar" and q["fase"] == "votando":
                q["fase"] = "resuelta"
            elif a == "siguiente" and q["fase"] == "resuelta":
                if q["q"] + 1 < PREGUNTAS:
                    q["q"], q["fase"] = q["q"] + 1, "votando"
                else:
                    q["fase"] = "fin"
            elif a == "reiniciar":
                q.update(ronda=q["ronda"] + 1, q=0, fase="espera", votos=[{} for _ in range(PREGUNTAS)])
            elif a not in ("abrir", "cerrar", "siguiente"):
                raise ValueError
        emite_estado()
        return self._json({"fase": estado["quiz"]["fase"]})

    def _votar(self, d):
        try:
            cid, n, o = str(d["cid"])[:64], int(d["q"]), int(d["o"])
        except (KeyError, TypeError, ValueError):
            return self.send_error(400, "Voto mal formado")
        with cerrojo:
            q = estado["quiz"]
            if q["fase"] != "votando" or n != q["q"] or not 0 <= o < OPCIONES or not cid:
                return self._json({"ok": False, "fase": q["fase"]}, 409)
            q["votos"][n][cid] = o
        emite_estado()
        return self._json({"ok": True})

    def _guion(self, d, _):
        n = str(int(d["n"]))
        with cerrojo:
            if d.get("borrar"):
                guion_vivo.pop(n, None)
            else:
                texto, rapidas = str(d["texto"])[:20000], [str(x)[:300] for x in d["rapidas"]][:12]
                guion_vivo[n] = {"texto": texto, "rapidas": rapidas}
            guarda_json(GUION_VIVO, guion_vivo)
            datos = {"n": int(n), **guion_vivo.get(n, {"borrar": True})}
        emite("guion", datos)
        print(f"{hora()}  {self.client_address[0]:<15} {'restaura' if d.get('borrar') else 'edita'} el guion de la diapositiva {n}", flush=True)
        return self._json({"ok": True})

    def _lab_accion(self, d, _):
        emite("lab_accion", {"lab": str(d["lab"]), "id": str(d["id"])})
        return self._json({"ok": True})

    def _lab_reenvia(self, d, ruta):
        """Parches y fotos del laboratorio: solo los acepta de la pizarra principal y los reparte a todos."""
        with cerrojo:
            if d.get("id") != principal():
                return self._json({"ok": False, "motivo": "no eres la pizarra principal"}, 409)
        emite("lab_parche" if ruta.endswith("parche") else "lab_foto", d)
        return self._json({"ok": True})

    def _lab_pedir(self, d):
        """Un espejo pide la foto de un laboratorio. Si llegan muchas a la vez (el público al entrar), se agrupan
        en una sola cada 0,3 s: la foto que manda la pizarra llega a todos."""
        lab = str(d.get("lab", ""))[:40]
        with cerrojo:
            falta = 0.3 - (time.time() - ultimo_pedido.get(lab, 0))
            if falta > 0:
                if lab not in pedidos_en_cola:
                    pedidos_en_cola.add(lab)
                    threading.Timer(falta, pide_foto, args=(lab,)).start()
                return self._json({"ok": True, "agrupado": True})
        return self._json({"ok": pide_foto(lab)})

    # ---------- Server-Sent Events ----------
    def _cerrada(self):
        """El navegador no envía nada por /eventos: si el socket se puede leer, es que ha cerrado la conexión."""
        try:
            legible, _, _ = select.select([self.connection], [], [], 0)
            return bool(legible) and not self.connection.recv(1, socket.MSG_PEEK)
        except OSError:
            return True

    def _eventos(self, vista, token):
        vista = vista if vista in VISTAS else "publico"
        if vista in CONTROL and not self._token_valido(token):
            return self.send_error(401, "Hace falta el PIN")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        yo, cola = secrets.token_hex(6), queue.SimpleQueue()
        ip = self.client_address[0]
        clave, mac = (ip, vista), mac_de(ip)
        with cerrojo:
            antes = principal()
            suscritos[yo] = {"cola": cola, "vista": vista, "desde": time.monotonic()}
            e = vistos.setdefault(clave, {"ip": ip, "vista": vista, "conectados": 0})
            e.update(mac=mac, visto=time.time(), conectados=e["conectados"] + 1)
        emite("hola", {"id": yo}, a=yo)
        emite_estado(cambia=False)
        print(f"{hora()}  {self.client_address[0]:<15} se conecta ({vista}){' · pizarra principal' if principal() == yo and antes != yo else ''}", flush=True)
        ultimo = time.monotonic()
        try:
            while not self._cerrada():
                try:
                    msg = cola.get(timeout=1)
                except queue.Empty:
                    msg = None
                if msg is None and time.monotonic() - ultimo < 15:
                    continue
                # cada 15 s sin novedades, un comentario mantiene viva la conexión a través de routers y proxies
                self.wfile.write(msg or b": sigo\n\n")
                while msg is not None:       # lo que se haya acumulado, de una vez
                    try:
                        msg = cola.get_nowait()
                        self.wfile.write(msg)
                    except queue.Empty:
                        msg = None
                self.wfile.flush()
                ultimo = time.monotonic()
                with cerrojo:
                    if clave in vistos:
                        vistos[clave]["visto"] = time.time()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            with cerrojo:
                suscritos.pop(yo, None)
                if clave in vistos:
                    vistos[clave].update(visto=time.time(), conectados=max(0, vistos[clave]["conectados"] - 1))
            emite_estado(cambia=False)
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


def carga_sesion(pin, nuevo, cero):
    try:
        guardado = json.loads(SESION.read_text(encoding="utf-8"))
        sesion.update(pin=guardado.get("pin"), tokens=guardado.get("tokens", []))
        previo = guardado.get("estado") or {}
        if isinstance(previo.get("i"), int) and not cero:
            estado.update(i=previo["i"], mov=previo.get("mov"))
            estado["crono"].update(previo.get("crono") or {})
            q = previo.get("quiz") or {}
            if len(q.get("votos", [])) == PREGUNTAS:
                estado["quiz"].update(q)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    if pin or nuevo or not sesion.get("pin"):
        sesion["pin"] = pin or f"{secrets.randbelow(10000):04d}"
        sesion["tokens"] = []                # con un PIN nuevo, todos vuelven a entrar
    guarda_sesion()
    try:
        guion_vivo.update(json.loads(GUION_VIVO.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--pin", help="PIN de 4 cifras para las vistas de control (por defecto, uno al azar que se recuerda)")
    ap.add_argument("--nuevo-pin", action="store_true", help="genera otro PIN y cierra las sesiones abiertas")
    ap.add_argument("--desde-cero", action="store_true", help="empieza en la diapositiva 1, con el cronómetro a cero y sin votos (tras un ensayo)")
    args = ap.parse_args()
    if args.pin and not (args.pin.isdigit() and len(args.pin) == 4):
        ap.error("el PIN debe tener 4 cifras")
    carga_sesion(args.pin, args.nuevo_pin, args.desde_cero)
    servidor = ThreadingHTTPServer(("0.0.0.0", args.puerto), functools.partial(Manejador, directory=str(AQUI)))
    servidor.daemon_threads = True
    ip, *otras = direcciones()
    base = f"http://{ip}:{args.puerto}"
    publico_url = f"{base}/p"
    print(f"Presentación del Reto 1 · ServiPass · puerto {args.puerto}")
    print(f"  PIN de los controles:  {sesion['pin']}")
    if estado["i"] or estado["crono"]["acum"] or any(estado["quiz"]["votos"]):
        print(f"  Sigue donde iba: diapositiva {estado['i'] + 1} (para empezar de nuevo: --desde-cero)")
    print(f"  Elegir vista:          {base}/")
    print(f"  Presentación (pizarra) {base}/presentacion.html")
    print(f"  PC (guion)             {base}/presentacion.html?vista=pc")
    print(f"  Móvil (mando)          {base}/presentacion.html?vista=mando")
    print(f"  Público (votar)        {publico_url}")
    if guion_vivo:
        print(f"  Guion con cambios guardados en {len(guion_vivo)} diapositiva(s): {GUION_VIVO.name}")
    if otras:
        print("  Si esa red no es la del aula, probar con:", ", ".join(f"http://{o}:{args.puerto}/" for o in otras))
    print("Ctrl+C para parar.", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nParado.")
