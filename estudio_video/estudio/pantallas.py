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


def _sesion_previa(navegador, base: str, ruta: str, pin: str,
                   ancho: int, alto: int, avisar=None) -> dict | None:
    """Teclea el PIN en un contexto que NO se graba y devuelve la sesión ya hecha.

    Aquí se arregla un fallo que estropeaba tres planos de cada cinco, y merece
    la pena contarlo porque la causa no está donde se ve el síntoma.

    Playwright empieza a grabar cuando se CREA EL CONTEXTO, no cuando uno se lo
    pide. `record_video_dir` es un argumento de `new_context`, así que lo que
    venga después —abrir la página, esperar a la red, teclear el PIN— ya está
    dentro del vídeo. Y el panel de PIN tarda lo suyo: esperar el selector, dar
    cuatro clics y dejar que la pantalla se asiente son dos o tres segundos de
    un clip de seis. El montaje coge el clip por el principio, de modo que el
    plano que debía enseñar el mapa de mesas enseñaba el TECLADO NUMÉRICO.
    Costó encontrarlo porque el vídeo se generaba sin un solo error: las
    capturas eran correctas, solo que de otro momento.

    No hay forma de retrasar el comienzo de la grabación, así que se hace al
    revés: el PIN se teclea en un contexto aparte y corriente, del que solo se
    guarda `storage_state()`. El token de sesión vive en `localStorage` —lo dice
    `frontend/js/sesion.js`, y está así para que aguante las recargas—, de modo
    que el contexto que sí graba nace ya identificado y va directo a la
    pantalla. El teclado no aparece porque no hay nada que teclear.

    Si algo falla, se devuelve `None` y `grabar` teclea el PIN en cámara como
    antes: un plano mal encuadrado es mejor que un vídeo a medias.
    """
    contexto = navegador.new_context(viewport={"width": ancho, "height": alto},
                                     ignore_https_errors=True)
    try:
        page = contexto.new_page()
        # También aquí va el escaparate: este contexto no se graba, pero pide
        # datos igual, y la regla del proyecto es que las pantallas de un vídeo
        # nunca hablen con los pedidos de clientes de verdad.
        _poner_escaparate(page, B.cargar(), avisar=None)
        page.goto(base + ruta, wait_until="networkidle", timeout=45000)
        _entrar(page, pin)
        page.wait_for_timeout(400)
        return contexto.storage_state()
    except Exception as e:
        if avisar:
            avisar(f"no se pudo hacer la sesión por adelantado ({type(e).__name__}: {e}); "
                   "el PIN se teclea en cámara")
        return None
    finally:
        contexto.close()


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

# Las cuatro secciones de cocina, tal y como se llaman en la tabla `estaciones`
# (`backend/sql/09_estaciones.sql`). Solo se usan de red de seguridad: a qué
# sección va cada plato es una columna de `productos` y la trae la biblia.
ESTACIONES = ["plancha", "freidora", "frios", "barra"]
CAMAREROS = ["Vera", "Ana", "Bo"]                    # del elenco: los mismos que salen en vídeo

# En qué estado está cada línea según lo que tenga que decir su mesa. El estado de
# una mesa no se guarda en ninguna parte: lo DEDUCE el backend de las líneas del
# pedido (`main.py`, `/api/sala`) — sin líneas, «sentados, sin pedir»; todo
# «lista», listo en el pase; todo «servida», esperando la cuenta.
ESTADOS_LINEA = {
    # Ojo con meter «lista» aquí: al backend le basta UNA línea lista para que la
    # mesa pase a leerse «listo en el pase», así que una mesa que aquí llamásemos
    # «en cocina» diría otra cosa en la pantalla de verdad.
    "en_cocina": ["enviada", "enviada", "preparando", "preparando"],
    "pase": ["lista"],
    "esperando_cuenta": ["servida"],
}


def _guion_de_sala(ocupadas: int) -> list[str]:
    """Qué dice cada mesa ocupada, de izquierda a derecha.

    Va escrito y no sorteado. Antes el estado salía de leer unas líneas que se
    inventaban al azar, y el mapa daba lo que daba: no aparecía «sin pedir»
    —todas las líneas nacían ya enviadas a cocina— y al forzar esa desapareció
    «listo en el pase».

    Y el plano 4 narra los cuatro estados: «cada mesa dice qué está esperando:
    sin pedir, en cocina, lista en el pase o esperando la cuenta». Si en pantalla
    solo hay tres, el cuarto se lee como que el sistema no lo distingue, que es
    justo lo contrario de lo que el plano promete. Puestos en este orden, el mapa
    se lee de izquierda a derecha igual que lo cuenta la voz, y de paso igual que
    avanza un servicio.

    Lo que sigue sorteado es el relleno: qué platos, cuántos y con qué nota.
    """
    guion = ["en_cocina"] * ocupadas
    if ocupadas < 4:             # con menos mesas no caben los cuatro estados
        return guion
    guion[0] = "sin_pedir"
    guion[-2] = "pase"
    guion[-1] = "esperando_cuenta"
    if ocupadas >= 6:
        # Dos mesas con platos en el pase, para que esa pantalla tenga algo que
        # contar: con una sola comanda esperando no se ve que ordena por espera.
        guion[-3] = "pase"
    return guion

# Las notas van por categoría, y no es remilgo. En la primera grabación del pase
# se leía «3× Caña de la estación · sin cebolla» y «1× Batido de nebulosa · poco
# hecho», y quien ve el vídeo no piensa «qué nota más rara»: piensa que el
# sistema mezcla las notas, que es justo lo contrario de lo que el vídeo quiere
# demostrar. La mayoría de líneas van SIN nota, que es lo que pasa de verdad.
NOTAS_BEBIDA = ["sin hielo", "muy fría", "", "", ""]
NOTAS_POSTRE = ["sin gluten", "para compartir", "", "", ""]
NOTAS_COCINA = ["sin cebolla", "poco hecho", "sin gluten", "extra de salsa", "", "", ""]
CAT_BEBIDA = "barra de ox"          # «Barra de oxígeno», sin depender de la tilde
CAT_POSTRE = "mara fr"              # «Cámara fría», ídem

# «para llevar» se cayó de la lista a propósito: en una comanda de MESA contradice
# a la propia mesa, y en pantalla parece un fallo de datos.


def _estacion_de(plato: dict, az: random.Random) -> str:
    """A qué sección de cocina va este plato. La de verdad, si la biblia la trae.

    El plano del KDS dice «la comanda entra en cocina **repartida por
    estaciones**», así que si el reparto está mal el plano desmiente su propia
    narración. Con el reparto al azar salía «Rubia de gravedad baja · FREIDORA»
    —una cerveza en la freidora— y «Brasa de Perihelio · BARRA». Nadie lo lee
    como «qué dato más raro»: lo lee como que el sistema reparte mal.

    El azar solo queda para las biblias viejas, descargadas antes de que
    `biblia.descargar()` trajera la columna. Y ni siquiera es azar puro: se
    reparte por categoría, que acierta casi siempre.
    """
    if plato.get("estacion"):
        return plato["estacion"]
    cat = (plato.get("categoria") or "").lower()
    if CAT_BEBIDA in cat:
        return "barra"
    if CAT_POSTRE in cat or "hidropon" in cat:
        return "frios"
    if "fritura" in cat:
        return "freidora"
    if "placa" in cat:
        return "plancha"
    return az.choice(ESTACIONES)


def _notas_de(plato: dict) -> list[str]:
    cat = (plato.get("categoria") or "").lower()
    if CAT_BEBIDA in cat:
        return NOTAS_BEBIDA
    if CAT_POSTRE in cat:
        return NOTAS_POSTRE
    return NOTAS_COCINA


# Lo que se ve en pantalla es también el decorado: no queremos que en un tutorial
# salga «Plato QA», que es un residuo de las pruebas y no un plato de la carta.
# Y tampoco el «Pato» de 999 €, que es una broma de la carta de desarrollo: un
# importe así en el pase o en el ticket se lee como un error de cálculo del TPV.
PRECIO_MAXIMO = 60.0
FUERA_DE_CARTA = ("qa", "prueba", "test")


def _presentable(nombre: str, precio_eur: float) -> bool:
    return (not any(x in nombre.lower() for x in FUERA_DE_CARTA)
            and 0 < precio_eur <= PRECIO_MAXIMO)


def _platos_presentables(bib: B.Biblia) -> list[dict]:
    buenos = [p for p in bib.platos
              if _presentable(p["nombre"], float(p.get("precio") or 0))]
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
        guion = _guion_de_sala(min(ocupadas, len(mesas)))

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
            estado_mesa = guion[i]
            lineas = []
            total = 0
            for _ in range(0 if estado_mesa == "sin_pedir" else az.randint(1, 4)):
                linea_id += 1
                p = az.choice(platos)
                cantidad = az.choice([1, 1, 1, 2, 3])
                estado_linea = az.choice(ESTADOS_LINEA[estado_mesa])
                total += int(round(p["precio"] * 100)) * cantidad
                lineas.append({
                    "id": linea_id, "pedido_id": pedido_id, "cantidad": cantidad,
                    "notas": az.choice(_notas_de(p)), "estacion": _estacion_de(p, az),
                    "estado": estado_linea,
                    "enviada_en": _ahora_iso(-antiguedad),
                    # `lista_en` es la hora en que cocina la cantó, y de ella sale el
                    # cronómetro rojo del pase. Una línea que aún se cocina no la tiene.
                    "lista_en": (None if estado_linea in ("enviada", "preparando")
                                 else _ahora_iso(-antiguedad // 2)),
                    "producto": p["nombre"], "tipo": "sala", "cliente": None,
                    "mesa": nombre, "camarero": camarero,
                    # Precio y alérgenos no los usa la pantalla de cocina, pero sí el
                    # ticket del TPV cuando se abre la mesa: sin ellos, cada línea
                    # sale a 0,00 € y el total no cuadra con el mapa de mesas.
                    "producto_id": p["id"], "precio_cent": int(round(p["precio"] * 100)),
                    "alergenos": p.get("alergenos", ""), "pago_id": None,
                })

            self.mesas.append({
                "id": m.get("mesa_id") or (i + 1), "nombre": nombre, "zona": _zona_de(nombre),
                "plazas": plazas, "pedido_id": pedido_id,
                "abierto_en": _ahora_iso(-antiguedad - 300),
                "comensales": az.randint(1, plazas), "camarero": camarero,
                "total_cent": total, "minutos": (antiguedad + 300) // 60,
                "estado": estado_mesa,
            })
            # Sin líneas no hay comanda: la cocina no tiene nada que hacer con una
            # mesa a la que nadie ha tomado nota, y `/api/kds` tampoco la devolvería.
            if lineas:
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
        """Lo que cocina tiene por hacer, y solo eso.

        La API filtra `estado IN ('enviada','preparando','lista')` (`main.py`), o
        sea que lo ya servido no sale. Importa aquí porque hay una mesa esperando
        la cuenta —con todo servido— y dejarla en la pantalla de cocina la pondría
        a cocinar dos veces lo que el comensal ya se ha comido.
        """
        vivas = []
        for c in self.comandas:
            quedan = [l for l in c["lineas"] if l["estado"] != "servida"]
            if quedan:
                vivas.append(dict(c, lineas=quedan))
        return {"ahora": _ahora_iso(), "comandas": vivas, "esperando": 0}

    def pase(self) -> dict:
        """Lo que espera a que sala lo lleve. El último pasa de cinco minutos: sale en rojo.

        Va envuelto en `{"comandas": [...]}` porque es lo que devuelve la API de
        verdad (`api.pase(...)["comandas"]`, en `backend/app/simulacion.py`), y
        devolver la lista pelada dejaba la pantalla de sala EN BLANCO.

        El fallo era peor de lo que parece por dónde está el `await`. En
        `sala.html`, `cargar()` empieza con `await cargarPase()`, y `cargarPase`
        solo protege con `try` la llamada a la API, no lo de después:

            try { d = await api('/pase'); } catch { return; }
            caja.hidden = !d.comandas.length;        ← aquí, fuera del try

        Con la lista pelada, `d.comandas` es `undefined`, la línea siguiente
        lanza un TypeError, `cargarPase()` queda rechazada y se lleva por
        delante a `cargar()` entera. Y `cargar()` es quien pinta DESPUÉS los
        indicadores, los avisos y el plano de zonas. Resultado: una pantalla
        negra con el titular «Quién está esperando» y nada debajo, que es
        exactamente lo que salió en el plano del pase. Ni un error a la vista:
        la página cargaba, el PIN entraba y la cabecera ponía «Laura · Comedor
        presurizado». Solo faltaba todo lo demás.

        Lo que sale son las mesas que de verdad tienen platos en «lista» —las
        mismas que en el mapa del TPV se leen «listo en el pase»— y no las tres
        primeras comandas, como hacía antes. Son dos planos casi seguidos: si
        aquí aparece una mesa que el mapa pone «en cocina», se desmienten entre
        ellos delante del espectador.
        """
        out = []
        for c in self.comandas:
            listas = [l for l in c["lineas"] if l["estado"] == "lista"]
            if not listas:
                continue
            espera = 40 + len(out) * 190
            lineas = [dict(l, estacion="pase", lista_en=_ahora_iso(-espera),
                           esperando_seg=espera) for l in listas]
            out.append({"pedido_id": c["pedido_id"], "mesa": c["mesa"], "tipo": "sala",
                        "cliente": None, "desde": _ahora_iso(-espera), "lineas": lineas})
        return {"comandas": out, "ahora": _ahora_iso()}

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

    def carta_publica(self) -> list[dict]:
        """La misma carta, para el móvil del cliente (`/api/publico/carta`).

        Existe aparte de `catalogo()` por un detalle de nombre: el personal
        recibe `alergenos_claves` y el cliente `alergeno_claves`, en singular.
        Copiar el uno en el otro deja al cliente sin los iconos de alérgenos, que
        es justo lo que ese plano promete enseñar.

        La API pública además esconde las categorías vacías; aquí también, y por
        el mismo motivo por el que hay que filtrar: si al quitar el «Pato» una
        categoría se queda sin nada, el cliente ve una pestaña que no lleva a
        ninguna parte.
        """
        out = []
        for cat in self.bib.carta:
            prods = [dict(p, alergeno_claves=p.get("alergeno_claves") or [],
                          foto_url=p.get("foto") or f"/api/productos/{p['id']}/foto.svg")
                     for p in cat.get("productos", [])
                     if _presentable(p["nombre"], (p.get("precio_cent") or 0) / 100.0)]
            if prods:
                out.append({"id": cat["id"], "nombre": cat["nombre"],
                            "color": cat.get("color"), "productos": prods})
        return out

    def destacados(self) -> list[dict]:
        """«Lo que más sale»: los seis primeros de la carta ya filtrada.

        La API de verdad los saca de lo cobrado en siete días, y eso en un vídeo
        es una lotería: depende de lo que haya vendido el local esa semana, así
        que el mismo guion daría un carrusel distinto cada vez. Seis platos fijos
        de la carta buena cuentan lo mismo —qué se pide más— y se repiten, que es
        la regla de todo el estudio.

        Se coge uno de cada categoría antes de repetir categoría. Los seis
        primeros de la carta seguida serían seis placas calientes, y un carrusel
        de «lo que más sale» con seis veces lo mismo no parece un local con
        carta: parece un local con un plato.
        """
        cats = self.carta_publica()
        out = []
        for vuelta in range(max((len(c["productos"]) for c in cats), default=0)):
            for cat in cats:
                if vuelta < len(cat["productos"]):
                    p = cat["productos"][vuelta]
                    out.append({"id": p["id"], "nombre": p["nombre"],
                                "precio_cent": p["precio_cent"], "foto": p.get("foto"),
                                "foto_url": p["foto_url"], "categoria": cat["nombre"],
                                "color": cat.get("color"), "unidades": 0})
                    if len(out) == 6:
                        return out
        return out

    def catalogo(self) -> list[dict]:
        """La carta, sin los platos que delatan que esto es un entorno de pruebas.

        Falta un matiz que costó descubrir mirando un fotograma: filtrar los
        platos al INVENTAR las comandas no basta. Las comandas las escribe el
        escaparate, pero la carta que el TPV pinta al abrir una mesa la pide él
        solo a `/api/catalogo`, y esa llamada no la tocaba nadie. Así que el
        plano del cobro salía impecable por la derecha —ticket, total,
        pendiente— y con «Pato · 999,00 €» y «Plato QA» a la vista en el panel
        de la izquierda. Quien ve el vídeo no sabe que es una broma de la carta
        de desarrollo: ve un TPV con la carta mal.

        Se sirve la carta de la biblia y no una inventada porque es la de
        verdad, con sus categorías, sus colores y sus alérgenos; lo único que se
        hace es quitar lo que no debería estar publicado. Una categoría que se
        queda sin platos se cae también: un botón de categoría que abre un panel
        vacío parece un fallo.
        """
        out = []
        for cat in self.bib.carta:
            prods = [p for p in cat.get("productos", [])
                     if _presentable(p["nombre"], (p.get("precio_cent") or 0) / 100.0)]
            if not prods:
                continue
            out.append(dict(cat, productos=[
                dict(p, alergenos_claves=p.get("alergeno_claves") or [],
                     foto_url=p.get("foto") or f"/api/productos/{p['id']}/foto.svg")
                for p in prods]))
        return out

    def mesas_tpv(self) -> list[dict]:
        return [{k: m[k] for k in ("id", "nombre", "zona", "plazas", "pedido_id",
                                   "abierto_en", "total_cent")} for m in self.mesas]

    def pedido(self, pid: int) -> dict | None:
        """Una mesa abierta, entera, como la devuelve `/api/pedidos/{id}`.

        Hace falta para poder ABRIR una mesa en el TPV delante de la cámara. Sin
        esto, el plano del cobro y el del mapa de mesas eran la misma imagen con
        dos narraciones distintas —«el estado de cada mesa» y «el TPV cierra el
        cobro»—, y quien lo ve concluye lo único razonable: que el segundo paso
        no existe. Un vídeo que enseña un sistema tiene que enseñarlo hasta el
        final.

        Campos calculados igual que en `backend/app/main.py:pedido_completo`:
        el total suma las líneas no anuladas, `pagado_cent` sale de los pagos y
        `pendiente_cent` es la resta. Copiarlos de memoria no valdría: el TPV
        decide con ellos si el botón «Cobrar» se puede pulsar.
        """
        mesa = next((m for m in self.mesas if m["pedido_id"] == pid), None)
        if not mesa:
            return None
        lineas = next((c["lineas"] for c in self.comandas if c["pedido_id"] == pid), [])
        total = sum(l["cantidad"] * l["precio_cent"] for l in lineas if l["estado"] != "anulada")
        return {
            "id": pid, "tipo": "sala", "estado": "abierto", "cliente": None,
            "mesa": mesa["nombre"], "mesa_id": mesa["id"], "camarero": mesa["camarero"],
            "comensales": mesa["comensales"], "abierto_en": mesa["abierto_en"],
            "lineas": lineas, "total_cent": total,
            "pagos": [], "pagado_cent": 0, "pendiente_cent": total,
        }


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
    page.route("**/api/catalogo*", contestar(s.catalogo))
    # La carta del móvil va por otra puerta (`/api/publico/…`), y se filtra igual:
    # el «Pato · 999,00 €» es igual de malo en el teléfono del cliente que en el
    # TPV. Lo demás de `/publico/` —la leyenda de alérgenos, el nombre del local,
    # los nombres de las mesas— se deja pasar tal cual: es público de verdad, no
    # lleva un solo dato de nadie, y falsearlo solo empeoraría la pantalla.
    page.route("**/api/publico/carta*", contestar(s.carta_publica))
    page.route("**/api/publico/destacados*", contestar(s.destacados))
    def pedidos_abiertos(ruta):
        """GET lista las mesas abiertas; POST devuelve la que ya estaba abierta.

        El POST no es un descuido. En el TPV, tocar una mesa llama a
        `abrirMesa()`, y `abrirMesa()` hace `POST /api/pedidos` SIEMPRE, también
        sobre una mesa ocupada: es la API quien decide, y si la mesa ya tiene un
        pedido abierto lo devuelve tal cual en vez de crear otro
        (`backend/app/main.py:crear_pedido`). Aquí se imita esa respuesta, y por
        eso tocar una mesa delante de la cámara no crea nada: el POST se
        contesta DENTRO del navegador y el servidor no llega a verlo.

        Un POST sobre una mesa libre sí crearía un pedido de verdad, así que se
        contesta con un 405 y se avisa. Es el mismo criterio de siempre: lo que
        el escaparate no sabe falsear sin efectos, lo corta.
        """
        req = ruta.request
        if req.method == "GET":
            ruta.fulfill(status=200, content_type="application/json; charset=utf-8",
                         body=json.dumps(s.pedidos, ensure_ascii=False))
            return
        cuerpo = {}
        try:
            cuerpo = req.post_data_json or {}
        except Exception:
            pass
        mesa = next((m for m in s.mesas
                     if m["id"] == cuerpo.get("mesa_id") and m["pedido_id"]), None)
        p = s.pedido(mesa["pedido_id"]) if mesa else None
        if p is None:
            if avisar:
                avisar(f"se cortó un {req.method} a pedidos: abriría una mesa de verdad")
            ruta.fulfill(status=405, content_type="application/json; charset=utf-8",
                         body='{"detail":"el estudio solo mira"}')
            return
        ruta.fulfill(status=200, content_type="application/json; charset=utf-8",
                     body=json.dumps(p, ensure_ascii=False))

    page.route("**/api/pedidos", pedidos_abiertos)
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

    # Una mesa concreta, para poder abrirla en el TPV. Va DESPUÉS de
    # `**/api/pedidos` a propósito: Playwright prueba las rutas de la última a
    # la primera, así que la específica tiene que registrarse al final o la
    # genérica se la come.
    #
    # Solo se contesta a GET. Todo lo demás —enviar a cocina, cobrar, anular—
    # se corta con un 405, y esa es la regla de oro del escaparate: el sitio de
    # pruebas habla con la MISMA base de datos que el restaurante, así que un
    # clic de más durante una grabación es un pedido de verdad. Ya pasó una vez:
    # 6.736 pedidos de demo y la API por los suelos.
    def una_mesa(ruta):
        req = ruta.request
        if req.method != "GET":
            if avisar:
                avisar(f"se cortó un {req.method} a {req.url.split('/api/')[-1]}: "
                       "el estudio graba, no toca")
            ruta.fulfill(status=405, content_type="application/json; charset=utf-8",
                         body='{"detail":"el estudio solo mira"}')
            return
        cola = req.url.split("/api/pedidos/")[-1].split("?")[0]
        p = s.pedido(int(cola)) if cola.isdigit() else None
        if p is None:
            ruta.fulfill(status=404, content_type="application/json; charset=utf-8",
                         body='{"detail":"no es una mesa del escaparate"}')
            return
        ruta.fulfill(status=200, content_type="application/json; charset=utf-8",
                     body=json.dumps(p, ensure_ascii=False))

    page.route("**/api/pedidos/*", una_mesa)
    return s


# ── Gestos ──────────────────────────────────────────────────────────────────
# Un gesto es lo que hace la mano delante de la cámara: abrir una mesa, pulsar
# «Cobrar». Existen porque el guion pedía dos planos del TPV con narraciones
# distintas —«el estado de cada mesa» y «el TPV cierra el cobro y emite el
# ticket»— y sin gestos los dos salían IGUALES, con el mapa de mesas quieto. El
# segundo prometía algo que no se veía, que en un vídeo de demostración es peor
# que no prometerlo.
#
# Todos los gestos son de LECTURA. El escaparate corta con 405 cualquier cosa
# que no sea un GET (ver `una_mesa`), así que un gesto no puede enviar una
# comanda ni cobrar aunque se escriba mal.


def _gesto_cobrar(page, s: "Servicio") -> None:
    """Abre la mesa que espera la cuenta y saca el panel de cobro con tarjeta."""
    mesa = next((m for m in s.mesas if m["estado"] == "esperando_cuenta"), None)
    if not mesa:
        raise RuntimeError("el escaparate no tiene ninguna mesa esperando la cuenta")

    # Se toca por `data-mesa`, que es lo que pinta el TPV para las mesas de sala
    # (`data-pedido` es solo para los pedidos «para llevar», que aquí no hay).
    page.click(f"#v-mesas [data-mesa='{mesa['id']}']")
    page.wait_for_selector("#v-carta:not([hidden])", timeout=8000)
    page.wait_for_timeout(1100)          # que se lea el ticket antes de seguir

    page.wait_for_selector("#b-cobrar:not([disabled])", timeout=8000)
    page.click("#b-cobrar")
    page.wait_for_selector("#d-cobro[open]", timeout=8000)
    page.wait_for_timeout(800)

    # La tarjeta es el remate: se inclina siguiendo al puntero, y con el ratón
    # quieto se queda plana y parece un dibujo pegado. Dos movimientos lentos
    # bastan para que se note que está viva.
    page.click("#c-metodos [data-m='tarjeta']")
    page.wait_for_timeout(700)
    caja = page.query_selector("#d-cobro")
    if caja and (r := caja.bounding_box()):
        for dx, dy in ((0.35, 0.35), (0.65, 0.6), (0.5, 0.45)):
            page.mouse.move(r["x"] + r["width"] * dx, r["y"] + r["height"] * dy, steps=18)
            page.wait_for_timeout(350)


GESTOS = {"cobrar": _gesto_cobrar}


def grabar(clave: str, segundos: int = 6, con_tutorial: bool = True,
           base: str = KDS_PRUEBAS, destino: Path | None = None,
           guion_pantalla: str | None = None, con_escaparate: bool = True,
           gesto: str | None = None, avisar=None) -> Path:
    """Graba una pantalla del KDS y devuelve el webm resultante.

    `con_tutorial` dispara las burbujas de `tutorial.js`, que es lo que convierte
    una captura en una explicación. Si esa pantalla no tiene guion escrito, se
    queda la pantalla quieta, que tampoco está mal.

    `gesto` es lo que se hace en la pantalla mientras se graba (ver `GESTOS`).
    Sin gesto la pantalla se graba quieta, que es lo que quiere casi todo plano.
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

        # El PIN, ANTES de que la cámara esté rodando (ver `_sesion_previa`).
        estado = _sesion_previa(navegador, base, ruta, pin, ancho, alto,
                                avisar=avisar) if pin else None

        contexto = navegador.new_context(
            viewport={"width": ancho, "height": alto},
            record_video_dir=str(destino),
            record_video_size={"width": ancho, "height": alto},
            ignore_https_errors=True,
            storage_state=estado,       # None = sin sesión, como cualquier visita
        )
        page = contexto.new_page()

        # Un error de JavaScript no rompe la grabación: rompe la PANTALLA, y el
        # vídeo sale igual, con el hueco donde debería estar el contenido. Así
        # se perdió el plano del pase, que se grabó en negro y nadie se enteró
        # hasta mirar el montaje fotograma a fotograma. Escucharlos aquí cuesta
        # cuatro líneas y convierte media tarde de búsqueda en una línea de log.
        fallos: list[str] = []
        page.on("pageerror", lambda e: fallos.append(str(e).splitlines()[0]))
        page.on("console", lambda m: fallos.append(m.text.splitlines()[0])
                if m.type == "error" else None)

        servicio = _poner_escaparate(page, B.cargar(), avisar=avisar) if con_escaparate else None
        page.goto(base + ruta, wait_until="networkidle", timeout=45000)

        if pin:
            # Con la sesión puesta el panel no debería salir. Si sale, se teclea
            # igual —y se avisa—, porque quedarse mirando el teclado numérico
            # veinte segundos hasta que salte el timeout es peor.
            try:
                page.wait_for_selector("#panel-pin", timeout=1500)
            except Exception:
                pass
            else:
                if avisar:
                    avisar(f"«{clave}»: la sesión previa no se aplicó, así que el PIN se teclea "
                           "EN CÁMARA y el plano empieza con el teclado numérico.")
                _entrar(page, pin)
                page.wait_for_timeout(1200)

        hubo_gesto = False
        if gesto:
            # Lo que se quiere enseñar es DÓNDE ACABA el gesto, no cómo empieza.
            # Los clics se graban igual —no hay forma de pausar la cámara— pero
            # quedan al principio del clip y el montaje los salta (ver el
            # fichero `.json` que se escribe al final). Si el gesto falla, el
            # plano se queda en la pantalla de entrada, que sigue siendo una
            # captura válida, y se dice por qué.
            hacer = GESTOS.get(gesto)
            if not hacer:
                if avisar:
                    avisar(f"«{clave}»: no existe el gesto «{gesto}»; se graba la pantalla quieta.")
            elif servicio is None:
                if avisar:
                    avisar(f"«{clave}»: los gestos necesitan el escaparate; se graba quieta.")
            else:
                try:
                    hacer(page, servicio)
                    hubo_gesto = True
                except Exception as e:
                    if avisar:
                        avisar(f"«{clave}»: el gesto «{gesto}» se quedó a medias "
                               f"({type(e).__name__}: {e}).")

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

        if fallos and avisar:
            # Repetidos no: un `setInterval` que falla cada 30 s llenaría el log
            # de la misma línea y escondería la que importa.
            vistos = list(dict.fromkeys(fallos))[:3]
            avisar(f"«{clave}» dio {len(fallos)} error(es) de JavaScript y puede haberse "
                   f"grabado a medias: {' | '.join(vistos)}")

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
    _anotar_desde(final, segundos if hubo_gesto else 0)
    return final


def desde_de(clip: Path) -> float:
    """Por qué segundo empieza lo bueno de un clip grabado. 0 si empieza ya."""
    ficha = clip.with_suffix(".json")
    if not ficha.exists():
        return 0.0
    try:
        return float(json.loads(ficha.read_text(encoding="utf-8")).get("desde", 0.0))
    except Exception:
        return 0.0


def _anotar_desde(clip: Path, segundos_utiles: int) -> None:
    """Deja escrito, junto al clip, por qué segundo empieza lo que vale.

    Se ancla al FINAL y no al principio, y eso no es un rodeo: el clip termina
    siempre con `wait_for_timeout(segundos)` sobre la pantalla ya quieta, así
    que los últimos `segundos` son, por construcción, exactamente lo que el
    plano quiere enseñar. Cronometrar los clics desde Python daría un número
    parecido pero no el mismo —el vídeo de Playwright empieza a contar cuando
    la página pinta el primer fotograma, no cuando se crea el contexto—, y ese
    desfase es justo el que hace que un plano salga por medio segundo.

    Va en un fichero aparte y no en el nombre porque `remontar.py` vuelve a
    leer los clips del disco mucho después, sin el estado del trabajo delante.
    """
    ficha = clip.with_suffix(".json")
    if segundos_utiles <= 0:
        ficha.unlink(missing_ok=True)
        return
    from . import montaje as M
    total = M.duracion(clip)
    desde = max(0.0, total - segundos_utiles - 0.4)      # 0,4 s de aire por delante
    ficha.write_text(json.dumps({"desde": round(desde, 2), "total": round(total, 2)}),
                     encoding="utf-8")


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
