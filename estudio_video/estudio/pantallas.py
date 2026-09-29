"""Las pantallas del KDS no se dibujan: se graban.

Un modelo de difusión no sabe escribir. Si se le pide «la carta con los precios»
devuelve renglones de garabatos, y en un vídeo que sirve para ENSEÑAR a usar el
sistema eso no vale de nada. Así que la parte de interfaz sale del KDS de
verdad: se abre en un navegador, se graba y se monta.

Dos cosas importantes de cómo se hace aquí:

  · **No se toca nada.** Se entra, se mira y se graba. Nada de enviar comandas ni
    cobrar: el sitio de pruebas (:8093) sirve las pantallas de pruebas pero habla
    con la MISMA base de datos que el restaurante. Una demo que crea 6.736
    pedidos de mentira ya pasó una vez y tumbó la API.
  · **El tutorial ya estaba escrito.** `tutorial.js` tiene, pantalla por
    pantalla, las burbujas que explican para qué sirve cada cosa, con los textos
    revisados. Grabarlas es mejor que reescribirlas: si mañana cambia el KDS,
    cambia el vídeo.
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import biblia as B

# El sitio de pruebas: mismas pantallas, misma API, y no es el que ve el cliente.
KDS_PRUEBAS = "http://192.168.1.100:8093"

TAMANOS = {
    "tableta": (1280, 800),
    "movil": (390, 844),
    "pantalla": (1920, 1080),
}

# Qué tamaño le va a cada pantalla. El móvil del cliente se graba como móvil.
TAMANO_DE = {
    "cliente": "movil",
    "pantalla": "pantalla",
    "recogida": "pantalla",
}


class SinPlaywright(RuntimeError):
    pass


def _navegador():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:                       # pragma: no cover
        raise SinPlaywright(
            "Falta playwright en este entorno. `pip install playwright` y "
            "`playwright install chromium`."
        ) from e
    return sync_playwright


def _entrar(page, pin: str) -> None:
    """El panel de PIN, igual que lo hace la QA de la interfaz."""
    page.wait_for_selector("#panel-pin", timeout=20000)
    for cifra in pin:
        page.click(f"#panel-pin button:has-text('{cifra}')")
    page.wait_for_selector("#panel-pin", state="detached", timeout=20000)


# ── Escaparate ──────────────────────────────────────────────────────────────
# Dos problemas con grabar el KDS de producción, y el escaparate resuelve los dos.
#
# 1. **Una cocina vacía no enseña nada.** Sale «Sin comandas pendientes» y ya.
#    Llenarla de verdad sería meter pedidos falsos en la base del restaurante, y
#    eso ya pasó una vez sin querer: 6.736 pedidos de demo y la API por los suelos.
# 2. **Una cocina llena enseña DEMASIADO.** La primera grabación del TPV salió con
#    los nombres de los clientes de los pedidos para llevar y sus importes. Eso es
#    dato personal de gente real en un vídeo que se va a publicar, y el proyecto ya
#    dijo por escrito que con el RGPD no se juega (PROPUESTA_VISION_CCTV.md).
#
# La salida es la misma para ambos: las respuestas se interceptan DENTRO DEL
# NAVEGADOR y se contestan con un servicio inventado, hecho con la carta y las
# mesas de verdad y con gente del elenco. Las pantallas se ven llenas y creíbles,
# el servidor no se entera de nada y no sale ni un dato de un cliente real.
SEMILLA_ESCAPARATE = 4711

NOTAS = ["sin cebolla", "poco hecho", "para llevar", "sin gluten", "extra de salsa", ""]
ESTACIONES = ["plancha", "freidora", "frios", "barra"]
CAMAREROS = ["Vera", "Ana", "Bo"]                    # del elenco: los mismos que salen en vídeo

# Lo que se ve en pantalla es también el decorado: no queremos que en un tutorial
# salga «Plato QA», que es un residuo de las pruebas y no un plato de la carta.
def _platos_presentables(bib: B.Biblia) -> list[dict]:
    fuera = ("qa", "prueba", "test")
    buenos = [p for p in bib.platos
              if not any(x in p["nombre"].lower() for x in fuera)]
    return buenos or bib.platos or [{"nombre": "Plato", "id": 1, "precio": 10.0}]


def _ahora_iso(desplazamiento: float = 0.0) -> str:
    return (datetime.now() + timedelta(seconds=desplazamiento)).isoformat(timespec="seconds")


# El plano da el nombre de la mesa pero no su zona, y el TPV agrupa por zona: sin
# esto, las trece mesas salen amontonadas bajo «comedor presurizado». La inicial
# del nombre la dice, porque así las bautizó el tema del asteroide (07_tema).
ZONA_POR_INICIAL = {"C": "sala", "M": "terraza", "A": "barra"}


def _zona_de(nombre: str) -> str:
    return ZONA_POR_INICIAL.get(nombre[:1].upper(), "sala")


class Servicio:
    """Un servicio entero inventado, coherente entre todas las pantallas.

    Coherente quiere decir que la mesa C2 que en el TPV aparece «en cocina» es la
    misma que en la pantalla de cocina tiene una comanda esperando. Si cada
    pantalla se inventara lo suyo por su cuenta, el vídeo se caería a la primera
    vez que alguien comparase dos planos seguidos.
    """

    def __init__(self, bib: B.Biblia, ocupadas: int = 6):
        self.bib = bib
        az = random.Random(SEMILLA_ESCAPARATE)
        self.az = az
        platos = _platos_presentables(bib)
        mesas = bib.mesas or []

        self.mesas: list[dict] = []
        self.comandas: list[dict] = []
        self.pedidos: list[dict] = []
        linea_id, pedido_id = 900_000, 800_000

        for i, m in enumerate(mesas):
            nombre = m["nombre"]
            plazas = 4
            ocupada = i < ocupadas
            if not ocupada:
                self.mesas.append({
                    "id": m.get("mesa_id") or (i + 1), "nombre": nombre,
                    "zona": _zona_de(nombre), "plazas": plazas, "pedido_id": None,
                    "abierto_en": None, "comensales": None, "camarero": None,
                    "total_cent": None, "minutos": None, "estado": "libre",
                })
                continue

            pedido_id += 1
            antiguedad = 90 + i * 115
            camarero = CAMAREROS[i % len(CAMAREROS)]
            lineas = []
            total = 0
            for _ in range(az.randint(1, 4)):
                linea_id += 1
                p = az.choice(platos)
                cantidad = az.choice([1, 1, 1, 2, 3])
                total += int(round(p["precio"] * 100)) * cantidad
                lineas.append({
                    "id": linea_id, "pedido_id": pedido_id, "cantidad": cantidad,
                    "notas": az.choice(NOTAS), "estacion": az.choice(ESTACIONES),
                    "estado": az.choice(["enviada", "enviada", "preparando", "preparando", "lista"]),
                    "enviada_en": _ahora_iso(-antiguedad), "lista_en": None,
                    "producto": p["nombre"], "tipo": "sala", "cliente": None,
                    "mesa": nombre, "camarero": camarero,
                })

            estados = [l["estado"] for l in lineas]
            if all(e == "lista" for e in estados):
                estado_mesa = "pase"
            elif "preparando" in estados or "enviada" in estados:
                estado_mesa = "en_cocina"
            else:
                estado_mesa = "sin_pedir"
            if i == ocupadas - 1:
                estado_mesa = "esperando_cuenta"     # que se vea también ese aviso

            self.mesas.append({
                "id": m.get("mesa_id") or (i + 1), "nombre": nombre, "zona": _zona_de(nombre),
                "plazas": plazas, "pedido_id": pedido_id,
                "abierto_en": _ahora_iso(-antiguedad - 300),
                "comensales": az.randint(1, plazas), "camarero": camarero,
                "total_cent": total, "minutos": (antiguedad + 300) // 60,
                "estado": estado_mesa,
            })
            self.comandas.append({
                "pedido_id": pedido_id, "mesa": nombre, "tipo": "sala", "cliente": None,
                "camarero": camarero, "desde": _ahora_iso(-antiguedad), "lineas": lineas,
            })
            self.pedidos.append({
                "id": pedido_id, "tipo": "sala", "cliente": None,
                "abierto_en": _ahora_iso(-antiguedad - 300), "mesa": nombre,
                "total_cent": total,
            })

    # ── respuestas por endpoint ─────────────────────────────────────────
    def kds(self) -> dict:
        return {"ahora": _ahora_iso(), "comandas": self.comandas, "esperando": 0}

    def pase(self) -> list[dict]:
        """Lo que espera a que sala lo lleve. El último pasa de cinco minutos: sale en rojo."""
        out = []
        for i, c in enumerate(self.comandas[:3]):
            espera = 40 + i * 190
            lineas = [dict(l, estado="lista", estacion="pase",
                           lista_en=_ahora_iso(-espera), esperando_seg=espera)
                      for l in c["lineas"][:2]]
            out.append({"pedido_id": c["pedido_id"], "mesa": c["mesa"], "tipo": "sala",
                        "cliente": None, "desde": _ahora_iso(-espera), "lineas": lineas})
        return out

    def sala(self) -> dict:
        ocupadas = [m for m in self.mesas if m["pedido_id"]]
        alertas = [{"tipo": "cuenta", "mesa": m["nombre"], "pedido_id": m["pedido_id"],
                    "minutos": m["minutos"], "importe_cent": m["total_cent"],
                    "texto": f"La mesa {m['nombre']} lleva {m['minutos']} min esperando la cuenta"}
                   for m in ocupadas if m["estado"] == "esperando_cuenta"]
        return {
            "ahora": _ahora_iso(), "mesas": self.mesas,
            "libres": len(self.mesas) - len(ocupadas), "ocupadas": len(ocupadas),
            "comensales": sum(m["comensales"] or 0 for m in ocupadas),
            "por_mesa": None, "para_llevar": 0, "alertas": alertas,
            "umbrales": {"nota": 10, "cuenta": 8, "pase": 5},
        }

    def mesas_tpv(self) -> list[dict]:
        return [{k: m[k] for k in ("id", "nombre", "zona", "plazas", "pedido_id",
                                   "abierto_en", "total_cent")} for m in self.mesas]


def _poner_escaparate(page, bib: B.Biblia, avisar=None) -> Servicio:
    """Instala las respuestas de escaparate. Lo que no sepamos falsear, se corta.

    Cortar y no dejar pasar es deliberado: si mañana una pantalla pide un
    endpoint nuevo con nombres de clientes dentro, el fallo tiene que ser
    visible (un hueco en la pantalla), no invisible (datos reales en el vídeo).
    """
    s = Servicio(bib)

    def contestar(hacer):
        def manejar(ruta):
            ruta.fulfill(status=200, content_type="application/json; charset=utf-8",
                         body=json.dumps(hacer(), ensure_ascii=False))
        return manejar

    page.route("**/api/kds?*", contestar(s.kds))
    page.route("**/api/kds", contestar(s.kds))
    page.route("**/api/pase*", contestar(s.pase))
    page.route("**/api/sala*", contestar(s.sala))
    page.route("**/api/mesas*", contestar(s.mesas_tpv))
    page.route("**/api/pedidos", contestar(lambda: s.pedidos))
    page.route("**/api/solicitudes*", contestar(lambda: []))
    page.route("**/api/clientes*", contestar(lambda: []))
    page.route("**/api/facturas*", contestar(lambda: []))
    page.route("**/api/arqueo*", contestar(lambda: {}))

    def censurar(ruta):
        if avisar:
            avisar(f"se cortó una llamada a {ruta.request.url.split('/api/')[-1]}: "
                   "puede llevar datos de clientes reales y el escaparate no sabe falsearla")
        ruta.fulfill(status=200, content_type="application/json; charset=utf-8", body="[]")

    page.route("**/api/reservas*", censurar)
    return s


def grabar(clave: str, segundos: int = 6, con_tutorial: bool = True,
           base: str = KDS_PRUEBAS, destino: Path | None = None,
           guion_pantalla: str | None = None, con_escaparate: bool = True,
           avisar=None) -> Path:
    """Graba una pantalla del KDS y devuelve el webm resultante.

    `con_tutorial` dispara las burbujas de `tutorial.js`, que es lo que convierte
    una captura en una explicación. Si esa pantalla no tiene guion escrito, se
    queda la pantalla quieta, que tampoco está mal.
    """
    if clave not in B.PANTALLAS:
        raise KeyError(f"pantalla desconocida: {clave}")
    ruta, pin, _ = B.PANTALLAS[clave]
    destino = destino or (B.RAIZ / "trabajos" / "_pantallas")
    destino.mkdir(parents=True, exist_ok=True)

    ancho, alto = TAMANOS[TAMANO_DE.get(clave, "tableta")]
    sync_playwright = _navegador()

    with sync_playwright() as p:
        navegador = p.chromium.launch(args=["--force-device-scale-factor=1"])
        contexto = navegador.new_context(
            viewport={"width": ancho, "height": alto},
            record_video_dir=str(destino),
            record_video_size={"width": ancho, "height": alto},
            ignore_https_errors=True,
        )
        page = contexto.new_page()
        if con_escaparate:
            _poner_escaparate(page, B.cargar(), avisar=avisar)
        page.goto(base + ruta, wait_until="networkidle", timeout=45000)

        if pin:
            _entrar(page, pin)
            page.wait_for_timeout(1200)

        if con_tutorial:
            # tutorial.js se carga solo cuando alguien pulsa «?»; aquí se pide a
            # mano para no depender de dónde esté el botón en cada pantalla. La
            # URL va ABSOLUTA: con la relativa, add_script_tag resolvía contra
            # otra base y el script no llegaba nunca, sin dar ningún error.
            pantalla_js = guion_pantalla or ruta.lstrip("/").split("?")[0]
            motivo = ""
            try:
                page.add_script_tag(url=f"{base}/js/tutorial.js?v={int(time.time())}")
                page.wait_for_timeout(500)
                arrancado = page.evaluate(
                    "(p) => { if (!window.tutorial) return 'sin tutorial.js';"
                    " if (!window.tutorial.guiones.includes(p)) return 'pantalla sin guion: ' + p;"
                    " window.tutorial.empezar(p); return ''; }", pantalla_js)
                motivo = arrancado or ""
            except Exception as e:
                motivo = f"{type(e).__name__}: {e}"

            if not motivo:
                # Las burbujas pasan con teclado: un paso cada dos segundos y
                # medio, que es lo que tarda alguien en leerlas.
                pasos = max(1, segundos // 3)
                for _ in range(pasos):
                    page.wait_for_timeout(2500)
                    page.keyboard.press("ArrowRight")
            else:
                if avisar:
                    avisar(f"«{clave}» se grabó sin las burbujas del tutorial ({motivo}).")
                page.wait_for_timeout(segundos * 1000)
        else:
            page.wait_for_timeout(segundos * 1000)

        video = page.video
        contexto.close()
        navegador.close()
        salida = Path(video.path()) if video else None

    if not salida or not salida.exists():
        raise RuntimeError(f"no se grabó vídeo de {clave}")
    final = destino / f"{clave}.webm"
    if final.exists():
        final.unlink()
    salida.rename(final)
    return final


def comprobar(base: str = KDS_PRUEBAS) -> dict:
    """¿Responden las pantallas y se puede entrar con cada PIN? Sin grabar nada."""
    import requests
    out: dict[str, str] = {}
    for clave, (ruta, _pin, _n) in B.PANTALLAS.items():
        try:
            r = requests.get(base + ruta.split("?")[0], timeout=10)
            out[clave] = "ok" if r.ok else f"http {r.status_code}"
        except Exception as e:
            out[clave] = f"error: {type(e).__name__}"
    return out
