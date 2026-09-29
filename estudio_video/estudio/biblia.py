"""La biblia del estudio: lo que NO cambia de un vídeo a otro.

Un modelo de difusión no recuerda nada. Si le pides dos veces «la cantina» te
dibuja dos cantinas distintas, con otras mesas, otra barra y otra carta. Por eso
aquí no se le pide la cantina: se le IMPONE.

Tres anclas, y las tres salen de datos, no de la imaginación del modelo:

  1. **La sala** — el plano de verdad, el que el encargado arrastra en
     `plano.html`, leído por `/api/plano`. De ahí sale un modelo 3D a escala y,
     de ese modelo, los mapas de profundidad que ControlNet usa para obligar al
     modelo a respetar muros, mesas y barra. Las medidas son las mismas SIEMPRE
     porque son las mismas medidas.
  2. **Las cámaras** — un puñado de encuadres fijos con su posición en metros.
     El guion elige entre ellos; no se inventan ángulos nuevos. Dos vídeos
     grabados «en el comedor» están grabados desde el mismo sitio.
  3. **El elenco** — personas fijas, con su retrato de referencia congelado en
     `biblia/elenco/`. IP-Adapter las mantiene reconocibles entre tomas.

Y una cuarta, que es la que no se negocia: **la carta y las pantallas no se
generan**. Un modelo SD1.5 no sabe escribir «Brasa de Perihelio · 11,90 €»; sale
un garabato. Los precios y los platos salen de `/api/publico/carta` y se
componen encima del vídeo con ffmpeg, o se graban del KDS de verdad.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DIR_BIBLIA = RAIZ / "biblia"
DIR_CONTROL = DIR_BIBLIA / "control"
DIR_ELENCO = DIR_BIBLIA / "elenco"

# Dónde está ComfyUI. El estudio vive en el repo del KDS y el motor vive aparte,
# en Kinemato, con su venv, sus 8 GB de pesos y su propio CUDA. Se dice aquí y no
# se deduce de la ruta del estudio: si se dedujera, mover la carpeta rompería la
# comunicación con el motor sin que ningún error lo explicara.
DIR_KINEMATO = Path(os.environ.get("KINEMATO", r"M:\CLAUDE\Kinemato"))
DIR_COMFY_ENTRADAS = DIR_KINEMATO / "references"    # de donde LoadImage lee
DIR_COMFY_SALIDAS = DIR_KINEMATO / "outputs"        # donde VHS_VideoCombine deja los clips
DIR_COMFY_TEMP = DIR_KINEMATO / "temp"

# El KDS del que se lee. El sitio de pruebas (:8093) sirve el mismo API, así que
# para LEER da igual; se deja el 80 porque es el que siempre está.
KDS_URL = "http://192.168.1.100"
KDS_PIN = "9999"                       # encargado: es el único rol que ve el plano entero

# ── Escala ──────────────────────────────────────────────────────────────────
# El plano del KDS va en milésimas (0..1000 de ancho y de alto) justamente para
# no tener decimales. Para levantar un 3D hace falta decidir cuánto mide el
# local de verdad: 16 m de lado, 256 m², que es lo que ocupan 13 mesas, una
# barra y una cocina sin que nadie tenga que pasar de lado.
LADO_METROS = 16.0
METROS_POR_MILESIMA = LADO_METROS / 1000.0

# Altura de cada cosa, en metros. Las zonas son suelo pintado: no levantan.
ALTURAS = {
    "muro": 3.0,
    "puerta": 2.1,
    "barra": 1.10,
    "mesa": 0.75,
    "equipo": 0.90,
    "zona": 0.0,
}
ALTURA_TECHO = 3.0

# Excepciones por nombre, porque no todo el mobiliario de una cocina mide igual.
ALTURAS_POR_NOMBRE = {
    "Pase": 1.05,
    "Cámara fría": 1.90,
    "Cámara de despensa": 2.10,
    "Lavado": 0.95,
}


# ── El estilo: el sufijo que va en TODOS los prompts ─────────────────────────
# Esto es «la misma línea» de la que hablaba el encargo. El usuario escribe la
# acción; el decorado, la luz, la óptica y la paleta los pone el estudio, y son
# idénticos en el primer vídeo y en el número cuarenta.
#
# En inglés a propósito: SD 1.5 entiende mucho peor el español, y describir ropa
# en inglés además evita marcar género donde no hace falta.
ESTILO = (
    "interior of a canteen inside an asteroid mining station, walls of carved "
    "grey rock reinforced with riveted steel ribs, warm amber service lighting "
    "from below, cold blue safety strips along the floor, dust motes in the air, "
    "cinematic film still, 35mm anamorphic lens, shallow depth of field, "
    "muted teal and amber palette, volumetric haze, photorealistic"
)

ESTILO_NEGATIVO = (
    "text, letters, watermark, signature, logo, ui, hud, subtitles, menu card, "
    "readable writing, distorted hands, extra fingers, extra limbs, deformed face, "
    "blurry, lowres, jpeg artifacts, cartoon, anime, illustration, 3d render, "
    "daylight, outdoors, sky, trees, grass, modern restaurant, fast food chain"
)

# Cómo sale el vídeo. Cambiar esto cambia TODOS los vídeos, que es justo la idea.
FORMATO = {
    "ancho": 640,          # lo que se genera; se escala a 1920x1080 en el montaje
    "alto": 360,
    "fps": 8,              # AnimateDiff v3 trabaja a 8; el montaje interpola a 24
    "fps_final": 24,
    "ancho_final": 1920,
    "alto_final": 1080,
    "pasos": 20,
    "cfg": 7.5,
    "muestreador": "euler",
    "planificador": "normal",
    "semilla_base": 90210,   # fija: dos veces el mismo guion = dos veces el mismo vídeo
}


# ── Las cámaras: encuadres fijos, en metros ─────────────────────────────────
@dataclass(frozen=True)
class Camara:
    clave: str
    nombre: str
    pos: tuple[float, float, float]      # x este, y sur, z arriba
    mira: tuple[float, float, float]
    fov: float = 55.0
    nota: str = ""                       # para qué sirve este encuadre
    sin_techo: bool = False              # mirar el local desde fuera: el techo estorba


CAMARAS: dict[str, Camara] = {c.clave: c for c in [
    Camara("entrada", "La entrada, desde dentro", (3.0, 11.8, 1.60), (2.9, 15.5, 1.45), 62,
           "Quien llega. La puerta de la galería al fondo."),
    Camara("comedor", "Comedor presurizado", (3.4, 9.2, 1.70), (3.4, 2.6, 1.00), 58,
           "Las mesas C1..C6 en fila. El plano general de sala."),
    Camara("mesa", "Una mesa, de cerca", (2.1, 4.8, 1.30), (3.3, 2.5, 0.80), 45,
           "Plano medio: la comida, el móvil, las manos. Para la app del cliente."),
    Camara("mirador", "Mirador de la fractura", (5.8, 9.8, 1.60), (1.4, 13.8, 1.40), 60,
           "El ventanal a la grieta del asteroide. El sitio bonito del local."),
    Camara("atraque", "El atraque (la barra)", (5.4, 6.8, 1.60), (8.4, 3.0, 1.15), 55,
           "La barra y la caja. Cobros y pedidos de paso."),
    Camara("pase", "El pase", (9.2, 8.8, 1.60), (12.8, 6.1, 1.15), 55,
           "Donde cocina deja el plato y sala lo recoge. El paso que se añadió."),
    Camara("cocina", "Cocina", (11.2, 9.6, 1.60), (12.2, 2.2, 1.10), 58,
           "Placa, fritura, cámara fría. Detrás del tabique."),
    Camara("recogida", "Zona de recogida", (14.6, 14.6, 1.60), (10.2, 9.0, 1.10), 60,
           "Pedidos para llevar. OJO: en el plano esta zona no tiene mostrador dibujado, "
           "así que el mueble lo pone el modelo y puede variar entre tomas. Para fijarlo, "
           "hay que añadir el mostrador en plano.html."),
    Camara("cenital", "El local entero, desde arriba", (8.0, 8.05, 13.0), (8.0, 8.0, 0.0), 68,
           "Para explicar dónde está cada cosa. El plano, pero habitado.", sin_techo=True),
]}


# ── El elenco: siempre la misma gente ───────────────────────────────────────
@dataclass(frozen=True)
class Personaje:
    clave: str
    nombre: str
    papel: str                 # cliente | sala | cocina | direccion
    retrato: str               # prompt del retrato de referencia (inglés)
    breve: str                 # cómo se nombra dentro de una escena (inglés)
    semilla: int               # fija: el retrato sale igual cada vez que se recasten


ELENCO: dict[str, Personaje] = {p.clave: p for p in [
    # Clientes
    Personaje("nadia", "Nadia Ostrov", "cliente",
              "portrait of a weathered veteran miner in a worn orange jumpsuit, short grey "
              "cropped hair, deep lines on the face, dust on the collar, neutral expression",
              "a veteran miner in a worn orange jumpsuit with short grey hair", 1001),
    Personaje("teo", "Teo Marchal", "cliente",
              "portrait of a young dock technician in a blue coverall, welding goggles pushed "
              "up on the forehead, dark curly hair, faint grease on one cheek",
              "a young dock technician in a blue coverall with goggles on the forehead", 1002),
    Personaje("suri", "Suri Malabar", "cliente",
              "portrait of a geologist in a green thermal jacket, long dark braid over one "
              "shoulder, rimless glasses, calm attentive look",
              "a geologist in a green thermal jacket with a long dark braid", 1003),
    Personaje("klaus", "Klaus Bergmann", "cliente",
              "portrait of a broad shouldered foreman with a full grey beard, high visibility "
              "vest over a dark thermal shirt, tired eyes",
              "a broad shouldered foreman with a grey beard and a high visibility vest", 1004),
    Personaje("iris", "Iris Fontaine", "cliente",
              "portrait of a cargo pilot in a battered leather flight jacket covered in patches, "
              "red hair shaved on one side, sharp confident expression",
              "a cargo pilot in a patched leather flight jacket with red hair shaved on one side", 1005),
    Personaje("bo", "Bo Tanaka", "cliente",
              "portrait of a young apprentice in an oversized grey coverall, knitted cap, "
              "round face, slightly nervous smile",
              "a young apprentice in an oversized grey coverall and a knitted cap", 1006),
    # Personal
    Personaje("vera", "Vera Solano", "sala",
              "portrait of a server in a black apron over a dark shirt, hair tied back, holding "
              "a rugged tablet, alert friendly expression",
              "a server in a black apron holding a rugged tablet", 2001),
    Personaje("dimo", "Dimo Krast", "cocina",
              "portrait of a cook in a white kitchen jacket with rolled sleeves, dark head scarf, "
              "forearms marked by old burns, focused expression",
              "a cook in a white kitchen jacket and dark head scarf", 2002),
    Personaje("ana", "Ana Ferrer", "direccion",
              "portrait of a floor manager in a dark buttoned shirt, short hair, reading glasses "
              "hanging from the collar, composed expression",
              "a floor manager in a dark buttoned shirt with reading glasses on the collar", 2003),
]}


# ── Las pantallas del KDS, para grabarlas de verdad ─────────────────────────
# Clave → (ruta, PIN necesario o None si es pública, cómo se llama en el guion).
PANTALLAS = {
    "inicio":    ("/index.html", "1111", "el menú de aplicaciones"),
    "tpv":       ("/tpv.html", "1111", "el TPV"),
    "sala":      ("/sala.html", "1111", "la pantalla de sala y el pase"),
    "kds":       ("/kds.html", "3333", "la pantalla de cocina"),
    "plano":     ("/plano.html", "9999", "el plano del local"),
    "carta":     ("/carta.html", "9999", "la carta"),
    "arqueo":    ("/arqueo.html", "9999", "el arqueo de caja"),
    "reservas":  ("/reservas.html", "1111", "las reservas"),
    "almacen":   ("/almacen.html", "9999", "el almacén"),
    "informe":   ("/informe.html", "9999", "los informes"),
    "cliente":   ("/cliente.html?mesa=3", None, "la carta del cliente en el móvil"),
    "recogida":  ("/recogida.html", None, "la pantalla de recogida"),
    "pantalla":  ("/pantalla.html", None, "la pantalla de mesa con el QR"),
}

PINES = {"camarero": "1111", "cocina": "3333", "encargado": "9999"}


# ── Carga ───────────────────────────────────────────────────────────────────
@dataclass
class Biblia:
    """Todo lo fijo, ya resuelto: plano, carta, cámaras, elenco."""
    plano: list[dict]
    carta: list[dict]
    local: dict = field(default_factory=dict)

    @property
    def mesas(self) -> list[dict]:
        return [e for e in self.plano if e["tipo"] == "mesa"]

    @property
    def platos(self) -> list[dict]:
        """Todos los productos disponibles, aplanados, con el precio en euros."""
        out = []
        for cat in self.carta:
            for p in cat.get("productos", []):
                if not p.get("disponible", 1):
                    continue
                out.append({
                    "id": p["id"],
                    "nombre": p["nombre"],
                    "categoria": cat["nombre"],
                    "precio": p["precio_cent"] / 100.0,
                    "alergenos": p.get("alergenos") or "",
                })
        return out

    def plato(self, nombre: str) -> dict | None:
        objetivo = nombre.strip().lower()
        for p in self.platos:
            if p["nombre"].lower() == objetivo:
                return p
        return None


def _login(url: str, pin: str, tiempo: int = 15) -> str:
    r = requests.post(f"{url}/api/login", json={"pin": pin}, timeout=tiempo)
    r.raise_for_status()
    token = r.json().get("token")
    if not token:
        raise RuntimeError(f"login sin token: {r.text[:200]}")
    return token


def _logout(url: str, token: str) -> None:
    # Que no se quede una sesión de encargado abierta por haber mirado el plano.
    try:
        requests.post(f"{url}/api/logout", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    except Exception:
        pass


def descargar(url: str = KDS_URL, pin: str = KDS_PIN) -> Biblia:
    """Trae plano y carta del KDS y los deja en `biblia/`.

    Se hace explícitamente, no en cada render: si el encargado mueve una mesa,
    los vídeos siguen saliendo iguales hasta que alguien decide actualizar. Un
    estudio que cambia de decorado solo no sirve para lo que se pide aquí.
    """
    DIR_BIBLIA.mkdir(parents=True, exist_ok=True)
    token = _login(url, pin)
    try:
        r = requests.get(f"{url}/api/plano", headers={"Authorization": f"Bearer {token}"}, timeout=20)
        r.raise_for_status()
        plano = r.json()["elementos"]
    finally:
        _logout(url, token)

    r = requests.get(f"{url}/api/publico/carta", timeout=20)
    r.raise_for_status()
    carta = r.json()

    local = {}
    try:
        r = requests.get(f"{url}/api/publico/ajustes", timeout=10)
        if r.ok:
            local = r.json()
    except Exception:
        pass

    (DIR_BIBLIA / "plano.json").write_text(json.dumps(plano, ensure_ascii=False, indent=1), encoding="utf-8")
    (DIR_BIBLIA / "carta.json").write_text(json.dumps(carta, ensure_ascii=False, indent=1), encoding="utf-8")
    (DIR_BIBLIA / "local.json").write_text(json.dumps(local, ensure_ascii=False, indent=1), encoding="utf-8")
    return Biblia(plano=plano, carta=carta, local=local)


def cargar() -> Biblia:
    """Lee la copia de `biblia/`. Si no hay copia, la baja."""
    f_plano = DIR_BIBLIA / "plano.json"
    f_carta = DIR_BIBLIA / "carta.json"
    if not (f_plano.exists() and f_carta.exists()):
        return descargar()
    local = {}
    f_local = DIR_BIBLIA / "local.json"
    if f_local.exists():
        local = json.loads(f_local.read_text(encoding="utf-8"))
    return Biblia(
        plano=json.loads(f_plano.read_text(encoding="utf-8")),
        carta=json.loads(f_carta.read_text(encoding="utf-8")),
        local=local,
    )


def altura_de(elemento: dict) -> float:
    """Cuánto levanta del suelo un elemento del plano, en metros."""
    if elemento["nombre"] in ALTURAS_POR_NOMBRE:
        return ALTURAS_POR_NOMBRE[elemento["nombre"]]
    return ALTURAS.get(elemento["tipo"], 0.0)


def a_metros(milesimas: float) -> float:
    return milesimas * METROS_POR_MILESIMA
