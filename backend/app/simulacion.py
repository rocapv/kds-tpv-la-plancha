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
from pathlib import Path

NOTAS = [None, None, None, "Sin cebolla", "Muy hecha", "Sin pepinillo", "Sin gluten", "Extra de queso"]
NOMBRES = ["Ana", "Joan", "Lucía", "Iker", "Marta", "Sergi", "Nerea", "Hugo"]   # tripulación de paso

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
        return {"estado": self.estado, "pedidos": len(self.creados),
                "cobrados": self.cobrados, "ritmo": self.ritmo}

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
            await api.avanzar_pedido(pid, None, cocina)
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

                # 1) entra un cliente
                if random.random() < 0.5:
                    pedido = await self._nuevo_pedido(camarero)
                    if pedido:
                        abiertos.append((pedido, reloj + random.uniform(120, 300) * self.ritmo))

                # 2) la cocina avanza una de las comandas más antiguas.
                # Solo toca las suyas: si hay una comanda de verdad en el pase, la simulación
                # no se la come.
                comandas = [c for c in api.kds(None, cocina)["comandas"]
                            if c["pedido_id"] in self.creados]
                if comandas:
                    elegida = random.choice(comandas[:4])
                    await api.avanzar_pedido(elegida["pedido_id"], None, cocina)

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

    async def _nuevo_pedido(self, camarero: dict) -> int | None:
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
        libres = [m for m in api.mesas(camarero) if not m["pedido_id"]]
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
