"""Simulación de actividad para la demo: play / pausa / reset desde la barra superior.

Es el `simulador.py` de siempre, pero metido dentro del servicio: en vez de abrir sesiones
y hablar por HTTPS, llama a las mismas funciones de la API que usan las pantallas. Así el
tribunal ve el sistema moverse solo (comandas que entran, cocina que avanza, caja que cobra)
sin tener que abrir una terminal.

Lo que crea queda anotado en un fichero aparte (`simulacion.json`), de modo que **reset**
borra exactamente los pedidos de la simulación y no toca ni un ticket real, aunque el
servicio se haya reiniciado por medio.
"""
import asyncio
import json
import os
import random
import time
from pathlib import Path

NOTAS = [None, None, None, "Sin cebolla", "Muy hecha", "Sin pepinillo", "Sin gluten", "Extra de queso"]
NOMBRES = ["Ana", "Joan", "Lucía", "Iker", "Marta", "Sergi", "Nerea", "Hugo"]   # tripulación de paso

# ── El cronómetro de los bots ──────────────────────────────────────────────────────────────
# Un servicio real no va a ritmo constante: hay rachas. Si todos los bots fueran al mismo paso
# la demo se vería plana, y si además coincidieran sus rachas se formaría un cuello de botella
# —la sala metiendo comandas a la vez que la cocina va floja— que acaba con una pantalla llena
# de tarjetas que nadie saca.
#
# Por eso cada bot lleva SU cronómetro: cambia de marcha cada 3 minutos, alternando fuerte y
# flojo, y arranca con un desfase propio, repartido dentro de su familia (sala / cocina) a lo
# largo del ciclo completo. Así, en cualquier momento, parte de la sala va fuerte mientras otra
# parte va floja, y lo mismo en cocina: hay ritmo, pero no se sincroniza nadie con nadie.
CICLO_MARCHA = 180.0                 # segundos que dura cada marcha (3 minutos)
FACTORES = {"fuerte": 0.45, "flojo": 1.9}    # multiplican la espera: <1 es ir más deprisa

# Dos válvulas de seguridad, que son las que garantizan que no haya atasco aunque el azar se
# ponga en contra. Las dos imitan lo que hace una cocina de verdad.
COLA_APURO = 6      # comandas en MI sección → el cocinero aprieta, vaya por donde vaya su ciclo
COLA_ATASCO = 25    # comandas en toda la cocina → la sala deja de sentar gente tan deprisa


def marcha_en(desfase: float, ahora: float) -> str:
    """Qué marcha le toca a un bot con ese desfase en ese instante.

    Función aparte y sin estado a propósito: así se puede comprobar en una prueba que dos bots
    con desfases distintos no van sincronizados, sin levantar la simulación entera.
    """
    return "fuerte" if int((ahora + desfase) // CICLO_MARCHA) % 2 == 0 else "flojo"


def repartir_desfases(cuantos: int) -> list[float]:
    """Desfases repartidos a lo largo del ciclo completo (fuerte + flojo = 2 marchas).

    Con cuatro camareros salen a 0, 90, 180 y 270 s: dos van fuerte mientras dos van flojos, y
    el relevo se va dando de uno en uno, no todos de golpe.
    """
    periodo = CICLO_MARCHA * 2
    return [periodo * i / max(1, cuantos) for i in range(cuantos)]

RASTRO = Path(os.environ.get("KDS_DATOS", Path.home() / ".local/share/kds-tpv")) / "simulacion.json"


class Simulacion:
    """Un único servicio simulado por proceso: play, pause, reset y el rastro de lo creado."""

    def __init__(self):
        self.estado = "parado"          # parado · corriendo · pausado
        self.tarea: asyncio.Task | None = None
        self.creados: list[int] = self._leer_rastro()
        self.cobrados = 0
        self.ritmo = 1.0                # 1.0 = ritmo de servicio real; <1 = más deprisa
        self.tarea_caja: asyncio.Task | None = None
        self.segundos_caja = 10         # la caja suena cada 10 s pase lo que pase
        # Un bot por área, no un único simulador global: el de la placa térmica solo saca
        # plancha, el del comedor solo atiende sus mesas. Es lo que pasa en un servicio real
        # y además prueba que los permisos por puesto funcionan.
        self.bots: dict[str, dict] = {}         # clave de área → ficha del bot
        self.tareas_bot: list[asyncio.Task] = []

    # ── rastro en disco ──
    def _leer_rastro(self) -> list[int]:
        try:
            return json.loads(RASTRO.read_text(encoding="utf-8"))["pedidos"]
        except Exception:
            return []

    def _guardar_rastro(self) -> None:
        try:
            RASTRO.parent.mkdir(parents=True, exist_ok=True)
            RASTRO.write_text(json.dumps({"pedidos": self.creados}), encoding="utf-8")
        except OSError:
            pass                        # el rastro es una comodidad, no una garantía

    def resumen(self) -> dict:
        bots = sorted(self.bots.values(), key=lambda b: (b["tipo"], b["area"]))
        marchas = {}
        for b in bots:
            marchas[b.get("marcha", "—")] = marchas.get(b.get("marcha", "—"), 0) + 1
        return {"estado": self.estado, "pedidos": len(self.creados),
                "cobrados": self.cobrados, "ritmo": self.ritmo,
                "ciclo_marcha": CICLO_MARCHA, "marchas": marchas, "bots": bots}

    # ── mandos ──
    def _podar_rastro(self) -> None:
        """El rastro viene de disco: puede citar pedidos que ya no existen (una restauración,
        un borrado a mano). Se queda solo con los que siguen en la base de datos."""
        from .db import q
        if not self.creados:
            return
        marcas = ",".join(["%s"] * len(self.creados))
        vivos = {f["id"] for f in q(f"SELECT id FROM pedidos WHERE id IN ({marcas})", self.creados)}
        if len(vivos) != len(self.creados):
            self.creados = [p for p in self.creados if p in vivos]
            self._guardar_rastro()

    async def play(self, ritmo: float | None = None):
        from .main import hub
        self._podar_rastro()
        if ritmo:
            self.ritmo = max(0.05, min(5.0, ritmo))
        if self.estado != "corriendo":
            self.estado = "corriendo"
        if not self.tarea or self.tarea.done():
            self.tarea = asyncio.create_task(self._servicio())
        self._levantar_bots()
        if not self.tarea_caja or self.tarea_caja.done():
            self.tarea_caja = asyncio.create_task(self._caja())
        await hub.emitir("simulacion", **self.resumen())
        return self.resumen()

    async def pause(self):
        from .main import hub
        if self.estado == "corriendo":
            self.estado = "pausado"
        await hub.emitir("simulacion", **self.resumen())
        return self.resumen()

    async def reset(self):
        """Para la simulación y borra SOLO los pedidos que ella misma creó."""
        from .db import conn
        from .main import hub
        self.estado = "parado"
        for t in ("tarea", "tarea_caja"):
            if getattr(self, t):
                getattr(self, t).cancel()
                setattr(self, t, None)
        for t in self.tareas_bot:
            t.cancel()
        self.tareas_bot = []
        self.bots = {}
        ids = list(self.creados)
        if ids:
            marcas = ",".join(["%s"] * len(ids))
            with conn() as c, c.cursor() as cur:
                cur.execute(f"DELETE FROM facturas WHERE pedido_id IN ({marcas})", ids)
                cur.execute(f"DELETE FROM pagos WHERE pedido_id IN ({marcas})", ids)
                cur.execute(f"DELETE FROM lineas_pedido WHERE pedido_id IN ({marcas})", ids)
                cur.execute(f"DELETE FROM pedidos WHERE id IN ({marcas})", ids)
                c.commit()
        borrados = len(ids)
        self.creados = []
        self.cobrados = 0
        self._guardar_rastro()
        await hub.emitir("simulacion", **self.resumen())
        await hub.emitir("kds")
        return {**self.resumen(), "borrados": borrados}

    # ── un bot por área ────────────────────────────────────────────────────
    def _quien_esta_en(self, puesto: str) -> dict | None:
        """La persona que el encargado ha puesto en ese puesto del plano. Si no hay nadie, el
        bot trabaja igual, pero con la primera persona del rol que corresponda: la demo no se
        para porque el plano esté vacío."""
        from .db import q1
        return q1("""SELECT id, nombre, rol FROM empleados
                     WHERE activo AND puesto=%s ORDER BY id LIMIT 1""", (puesto,))

    def _levantar_bots(self):
        """Mira el plano y las secciones de cocina y pone un bot en cada área con trabajo."""
        from .db import q
        if self.tareas_bot:
            return                                  # ya están levantados
        sala = q("""SELECT clave, nombre FROM puestos
                    WHERE rol_operativo='camarero' ORDER BY orden""")
        cocina = q("SELECT clave, nombre FROM estaciones WHERE activa ORDER BY orden")
        suplente_sala = self._quien("camarero")
        suplente_cocina = self._quien("cocina")
        # Los desfases se reparten DENTRO de cada familia: los camareros entre ellos y los
        # cocineros entre ellos. Si se repartieran todos juntos, con pocos bots podría tocar
        # toda la sala fuerte y toda la cocina floja a la vez, que es justo lo que se evita.
        desf_sala = repartir_desfases(len(sala))
        desf_cocina = repartir_desfases(len(cocina))
        for i, p in enumerate(sala):
            quien = self._quien_esta_en(p["clave"]) or suplente_sala
            if not quien:
                continue
            self.bots[f"sala:{p['clave']}"] = {
                "tipo": "sala", "area": p["nombre"], "clave": p["clave"],
                "empleado": quien["nombre"], "pedidos": 0, "cobros": 0, "ultimo": None,
                "desfase": round(desf_sala[i], 1), "marcha": marcha_en(desf_sala[i], time.monotonic())}
            self.tareas_bot.append(asyncio.create_task(self._bot_sala(p, quien)))
        for i, e in enumerate(cocina):
            quien = self._quien_esta_en(e["clave"]) or suplente_cocina
            if not quien:
                continue
            self.bots[f"cocina:{e['clave']}"] = {
                "tipo": "cocina", "area": e["nombre"], "clave": e["clave"],
                "empleado": quien["nombre"], "avances": 0, "ultimo": None,
                "desfase": round(desf_cocina[i], 1), "marcha": marcha_en(desf_cocina[i], time.monotonic())}
            self.tareas_bot.append(asyncio.create_task(self._bot_cocina(e, quien)))

    async def _espera(self, minimo: float, maximo: float, ficha: dict | None = None) -> bool:
        """Duerme lo suyo y dice si hay que seguir trabajando (False = simulación parada).

        Si se le pasa la ficha de un bot, la espera se multiplica por su marcha del momento:
        en «fuerte» tarda menos de la mitad, en «flojo» casi el doble. La marcha se apunta en
        la ficha para que se vea en la barra quién está apretando y quién no.
        """
        factor = 1.0
        if ficha is not None:
            marcha = marcha_en(ficha.get("desfase", 0.0), time.monotonic())
            # Una marcha forzada por las válvulas de seguridad manda sobre el cronómetro.
            forzada = ficha.pop("forzar", None)
            if forzada:
                marcha = forzada
            ficha["marcha"] = marcha
            factor = FACTORES.get(marcha, FACTORES["fuerte"] if marcha == "apuro" else 1.0)
        await asyncio.sleep(random.uniform(minimo, maximo) * self.ritmo * factor)
        return self.estado == "corriendo"

    def _cocina_pendiente(self, quien: dict) -> int:
        """Cuántas comandas hay esperando en TODA la cocina (para frenar a la sala)."""
        from . import main as api
        datos = api.kds(estacion=None, pantalla=None, limite=1, u=quien)
        return len(datos["comandas"]) + datos.get("esperando", 0)

    async def _bot_sala(self, puesto: dict, quien: dict):
        """Camarero de un área: sienta gente en SUS mesas y manda la comanda a cocina."""
        from . import main as api
        ficha = self.bots[f"sala:{puesto['clave']}"]
        try:
            while True:
                # Si la cocina está desbordada, este camarero baja el ritmo aunque le tocara ir
                # fuerte: seguir metiendo comandas en una cocina atascada no es ir más deprisa,
                # es hacer la cola más larga.
                try:
                    if self._cocina_pendiente(quien) >= COLA_ATASCO:
                        ficha["forzar"] = "flojo"
                        ficha["ultimo"] = "espera: cocina llena"
                except Exception:
                    pass
                if not await self._espera(8, 22, ficha):
                    continue
                try:
                    pid = await self._nuevo_pedido(quien, zona_puesto=puesto["clave"])
                    if pid:
                        ficha["pedidos"] += 1
                        ficha["ultimo"] = f"comanda #{pid}"
                except Exception as e:
                    ficha["ultimo"] = f"error: {e}"
        except asyncio.CancelledError:
            raise

    async def _bot_cocina(self, estacion: dict, quien: dict):
        """Cocinero de una sección: solo toca las líneas de SU sección, como en la vida real."""
        from . import main as api
        ficha = self.bots[f"cocina:{estacion['clave']}"]
        try:
            while True:
                if not await self._espera(4, 10, ficha):
                    continue
                try:
                    # Las llamadas van POR NOMBRE a propósito: estas funciones son endpoints y
                    # el día que a uno se le añada un parámetro en medio (pasó con `pantalla` y
                    # con `limite`), una llamada posicional mete el empleado donde no toca y el
                    # bot se cae en silencio.
                    datos = api.kds(estacion=estacion["clave"], pantalla=None, u=quien)
                    mias = [c for c in datos["comandas"] if c["pedido_id"] in self.creados]
                    if not mias:
                        continue
                    if len(mias) >= COLA_APURO:
                        ficha["forzar"] = "apuro"         # se le está acumulando: aprieta
                    elegida = mias[0]                     # la más antigua: el pase manda
                    await api.avanzar_pedido(elegida["pedido_id"], estacion=estacion["clave"],
                                             pantalla=None, u=quien)
                    ficha["avances"] += 1
                    ficha["cola"] = len(mias)
                    ficha["ultimo"] = f"#{elegida['pedido_id']}"
                except Exception as e:
                    ficha["ultimo"] = f"error: {e}"
        except asyncio.CancelledError:
            raise

    # ── la caja: un ticket cada diez segundos, pase lo que pase ──
    async def _caja(self):
        """Cobra un pedido cada `segundos_caja`. Si no hay ninguno listo, lo empuja hasta
        servido; si no hay ninguno abierto, se inventa uno. Así el informe y el arqueo se
        mueven a la vista durante la demo, sin esperar al ritmo del servicio."""
        from . import main as api
        camarero, cocina = self._quien("camarero"), self._quien("cocina")
        if not camarero or not cocina:
            return
        try:
            while True:
                await asyncio.sleep(self.segundos_caja)
                if self.estado != "corriendo":
                    continue
                try:
                    await self._cobrar_uno(api, camarero, cocina)
                except Exception as e:
                    from .main import hub
                    await hub.emitir("simulacion", **{**self.resumen(), "error": str(e)})
        except asyncio.CancelledError:
            raise

    async def _cobrar_uno(self, api, camarero: dict, cocina: dict):
        pid = next((p for p in self.creados
                    if (api.pedido_completo(p)["estado"] == "abierto"
                        and any(l["estado"] != "anulada" for l in api.pedido_completo(p)["lineas"]))), None)
        if pid is None:
            pid = await self._nuevo_pedido(camarero)
            if pid is None:
                return
        # la cocina saca lo que haga falta: enviada → preparando → lista → servida
        for _ in range(4):
            ped = api.pedido_completo(pid)
            if not any(l["estado"] in ("enviada", "preparando", "lista") for l in ped["lineas"]):
                break
            await api.avanzar_pedido(pid, estacion=None, pantalla=None, u=cocina)
        ped = api.pedido_completo(pid)
        if ped["estado"] != "abierto" or ped["pendiente_cent"] <= 0:
            return
        metodo = random.choice(["tarjeta", "tarjeta", "efectivo", "bizum"])
        cobro = api.Cobro(metodo=metodo,
                          entregado_cent=-(-ped["pendiente_cent"] // 500) * 500 if metodo == "efectivo" else None)
        await api.cobrar(pid, cobro, camarero)
        self.cobrados += 1
        from .main import hub
        await hub.emitir("simulacion", **self.resumen())

    # ── el servicio simulado ──
    def _quien(self, rol: str) -> dict | None:
        from .db import q1
        return q1("SELECT id, nombre, rol FROM empleados WHERE rol=%s AND activo ORDER BY id LIMIT 1", (rol,))

    async def _servicio(self):
        from . import main as api
        camarero, cocina = self._quien("camarero"), self._quien("cocina")
        if not camarero or not cocina:
            self.estado = "parado"
            return
        abiertos: list[tuple[int, float]] = []      # (pedido, momento de cobrarlo)
        try:
            while True:
                if self.estado != "corriendo":
                    await asyncio.sleep(0.4)
                    continue
                reloj = asyncio.get_event_loop().time()

                # El trabajo de sala y de cocina lo hacen los bots de cada área
                # (_bot_sala / _bot_cocina); aquí solo queda la caja.
                # 3) la caja cobra lo que ya se ha servido
                for pid, cuando in list(abiertos):
                    if reloj < cuando:
                        continue
                    ped = api.pedido_completo(pid)
                    if ped["estado"] != "abierto":
                        abiertos.remove((pid, cuando))
                        continue
                    if any(l["estado"] in ("enviada", "preparando") for l in ped["lineas"]):
                        continue
                    metodo = random.choice(["tarjeta", "tarjeta", "efectivo", "bizum"])
                    cobro = api.Cobro(metodo=metodo,
                                      entregado_cent=-(-ped["total_cent"] // 500) * 500 if metodo == "efectivo" else None)
                    await api.cobrar(pid, cobro, camarero)
                    abiertos.remove((pid, cuando))
                    self.cobrados += 1

                await asyncio.sleep(random.uniform(5, 15) * self.ritmo)
        except asyncio.CancelledError:
            raise
        except Exception as e:                      # un fallo de la demo no tumba el servicio real
            from .main import hub
            self.estado = "parado"
            await hub.emitir("simulacion", **{**self.resumen(), "error": str(e)})

    async def _nuevo_pedido(self, camarero: dict, zona_puesto: str | None = None) -> int | None:
        from . import main as api
        # Se agrupa por estación y no por el nombre de la categoría: la carta se puede
        # renombrar entera desde la aplicación (o desde el decorado) sin romper la demo.
        carta = {}
        for c in api.catalogo(False, camarero):
            for pr in c["productos"]:
                if pr["disponible"]:
                    carta.setdefault(pr["estacion"], []).append(pr)
        if not carta.get("plancha"):
            return None
        # Cada puesto de sala atiende su zona: el del mirador no sienta gente en el comedor.
        zonas = {"comedor": "sala", "mirador": "terraza", "atraque": "barra"}
        libres = [m for m in api.mesas(camarero) if not m["pedido_id"]]
        if zona_puesto in zonas:
            libres = [m for m in libres if m["zona"] == zonas[zona_puesto]] or libres
        if libres and random.random() > 0.25:
            mesa = random.choice(libres)
            ped = await api.crear_pedido(api.NuevoPedido(tipo="sala", mesa_id=mesa["id"]), camarero)
            comensales = random.randint(1, min(3, mesa["plazas"]))
        else:
            ped = await api.crear_pedido(api.NuevoPedido(tipo="llevar", cliente=random.choice(NOMBRES)), camarero)
            comensales = 1
        pid = ped["id"]
        self.creados.append(pid)
        self._guardar_rastro()
        for _ in range(comensales):
            for grupo, prob in (("plancha", 1.0), ("barra", 1.0), ("freidora", 0.7)):
                if carta.get(grupo) and random.random() <= prob:
                    await api.anadir_linea(
                        pid, api.NuevaLinea(producto_id=random.choice(carta[grupo])["id"],
                                            notas=random.choice(NOTAS)), camarero)
        await api.enviar_a_cocina(pid, camarero)
        return pid


simulacion = Simulacion()
