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
# CORTO a propósito. SD 1.5 lee 77 fichas de golpe y lo que va al principio pesa
# más: con el estilo largo de antes, el decorado se comía el prompt y la persona
# quedaba diluida hasta desaparecer —el primer clip salió con la sala perfecta y
# sin nadie dentro—. La sala ya la impone ControlNet, así que aquí solo hace
# falta el AMBIENTE: de qué está hecha la pared y cómo es la luz.
# El decorado también decide cuánto realismo se puede pedir. «Paredes de roca
# excavada en un asteroide» el modelo no lo ha fotografiado nunca: lo ha visto en
# ilustraciones y arte conceptual, y eso devolvía — escenas oscuras con aspecto
# de videojuego. «Comedor de tripulación de una estación», en cambio, se parece a
# cosas que sí existen y están fotografiadas: comedores de barco, de refinería,
# de base antártica. Misma ambientación, pero pedida con palabras que el modelo
# asocia a fotos. El cambio no costó ni un segundo de GPU y fue el segundo salto
# de calidad más grande, después de bajarle la fuerza a ControlNet.
ESTILO = (
    "photo of a crew mess hall on a space station, panelled walls, stainless steel, "
    "bright even lighting, cinematic film still, 35mm, photorealistic"
)

ESTILO_NEGATIVO = (
    "text, letters, watermark, signature, logo, ui, hud, subtitles, menu card, "
    "readable writing, distorted hands, extra fingers, extra limbs, deformed face, "
    "blurry, lowres, jpeg artifacts, cartoon, anime, illustration, 3d render, "
    "daylight, outdoors, sky, trees, grass, modern restaurant, fast food chain, "
    # La referencia de identidad arrastra el color de la ropa a toda la sala: en
    # una toma de alguien con chaqueta verde salieron verdes hasta las paredes.
    "monochrome, single colour scene, green tint, colour cast, tinted walls"
)

# Cómo sale el vídeo. Cambiar esto cambia TODOS los vídeos, que es justo la idea.
#
# SOBRE LA RESOLUCIÓN, que es la pregunta que siempre se hace: el vídeo SALE a
# 1920x1080, pero no se GENERA a 1920x1080, y no es lo mismo ni se puede hacer
# de otra manera aquí. SD 1.5 se entrenó a 512 px: pedirle 1080 de largo no da
# más detalle, da cuerpos duplicados y composiciones partidas, porque el modelo
# no sabe encuadrar a esa escala. Y AnimateDiff con 24 fotogramas a 1080 no
# entra en 11 GB ni de lejos.
#
# Lo que sí funciona, y es lo que hace todo el mundo con SD 1.5: generar donde
# el modelo compone bien y subir después con un modelo de superresolución
# (4x-UltraSharp), que INVENTA detalle en vez de estirar píxeles. El resultado
# es un 1080p de verdad, no un 640 ampliado.
FORMATO = {
    "ancho": 768,          # lo que se genera: el techo donde SD1.5 aún compone bien
    "alto": 432,
    "fps": 8,              # AnimateDiff v3 trabaja a 8; el montaje interpola a 24
    "fps_final": 24,
    "ancho_final": 1920,
    "alto_final": 1080,
    "pasos": 24,
    "cfg": 7.5,
    "muestreador": "euler",
    "planificador": "normal",
    "semilla_base": 90210,   # fija: dos veces el mismo guion = dos veces el mismo vídeo
    # «fijo»: cada plano se genera como imagen y el movimiento lo pone la cámara
    # en el montaje. «animado»: AnimateDiff mueve a la gente de verdad.
    # Medido el 29/09/2026 en la 1080 Ti, para un plano de tres segundos:
    #   fijo    → 36 s de GPU, imagen nítida, cara reconocible
    #   animado → 16,7 min, detalle hundido y escena apagada
    # 28 veces más caro para peor resultado, así que el movimiento lo ponía la
    # cámara.
    #
    # Puesto en «animado» el 01/10/2026 por decisión del encargo: los vídeos con
    # gente quieta no enseñan un servicio, y el coste de GPU es un problema menor
    # que un ejemplo que no se parece a lo que pasa en una sala. La medición de
    # arriba sigue siendo cierta y por eso se deja escrita; lo que cambió no es
    # el dato, es qué se prefiere pagar.
    # «wan» (01/10/2026): el plano se genera como imagen fija, con toda la
    # calidad, y después WAN 2.2 lo anima partiendo de ella. Sustituye a
    # «animado», que movía a la gente pero reinventaba la escena en cada
    # fotograma —sala que deriva, persona que se borra, detalle hundido— y
    # encima costaba 334 s de GPU por segundo de vídeo contra los 125 de WAN.
    # Más rápido y mejor, y ya no hay que elegir entre movimiento y calidad.
    "modo": "wan",
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
    breve: str                 # quién es, dentro de una escena (inglés)
    semilla: int               # fija: el retrato sale igual cada vez que se recasten
    # La ropa es parte del personaje, igual que la cara, y va SEPARADA a
    # propósito. Cuando iba dentro de `breve`, competía en la misma frase con la
    # acción y el modelo la reinterpretaba: el mismo hombre salía con chaleco
    # reflectante en una toma y con chaleco y pajarita en la siguiente. Aparte y
    # con su propio peso, se repite.
    vestuario: str = ""
    # Quién es, en español y en dos frases. No va al modelo de imagen: va a la
    # ficha, y sirve para que el guionista —y quien escriba el prompt— sepa qué
    # haría esta persona y qué no. Un elenco sin carácter acaba siendo cinco
    # maniquíes con ropa distinta.
    personalidad: str = ""
    # «h» o «m». Parece redundante —`breve` ya dice «a man», «a woman»— y no lo
    # es: esa palabra va en el prompt positivo, donde compite con la acción, el
    # ambiente y la ropa, y se pierde. Óliver, con barba escrita en su `breve`,
    # salió MUJER en un plano y hombre en el de al lado, misma cámara y misma
    # ficha. Este campo existe para poder decirlo también en el negativo, que es
    # donde la palabra no compite con nada. Ver `produccion.negativo_de`.
    sexo: str = ""


# Cinco moldes y no más: el camarero, dos clientes y dos clientas. Cuantas menos
# caras haya, más veces sale cada una, y cuantas más veces sale, antes nota
# cualquiera que es siempre la misma persona, que es justo de lo que va esto.
# Aquí el género SÍ va escrito: al modelo hay que decírselo o lo decide él, y
# entonces la misma clave sale hombre en una toma y mujer en la siguiente.
ELENCO: dict[str, Personaje] = {p.clave: p for p in [
    # Sala
    # En el retrato NO se nombra la tableta: mencionar un objeto que se sostiene
    # abre el plano, y la primera tanda salió de cintura para arriba y sin
    # coronilla. Los objetos van en `breve`, que es lo que se usa en las escenas.
    Personaje("oliver", "Óliver Sanz", "sala",
              "portrait of a man in his thirties, short dark hair, trimmed dark beard, "
              "black apron over a dark shirt, alert and friendly expression",
              "a waiter, a man in his thirties with short dark hair and a full dark beard", 2011,
              # Chaleco y camisa BLANCA, que es lo que hay en la hoja. La ficha
              # decía «delantal de peto sobre camisa gris» y la hoja nunca lo
              # tuvo: el retrato salió con chaleco desde la primera tanda. Ver la
              # nota de `vestuario` más abajo: manda la hoja.
              "wearing a dark waistcoat over a white shirt with the sleeves rolled up, "
              "dark trousers",
              "Ocho años detrás de la barra y se sabe los nombres. Habla poco y rápido, no "
              "pierde una comanda y no aguanta ver un plato enfriándose en el pase. Con los "
              "novatos tiene toda la paciencia del mundo.", sexo="h"),
    # Clientes
    Personaje("klaus", "Klaus Bergmann", "cliente",
              "portrait of a broad shouldered man in his fifties, full grey beard, high "
              "visibility vest over a dark thermal shirt, tired eyes, weathered skin",
              "a broad shouldered man in his fifties with a full grey beard", 1004,
              # Escrito como sale, no como se pidió: al pedir «chaleco naranja
              # sobre camisa oscura» el modelo devolvía, tomA tras toma, chaleco
              # gris sobre camisa naranja. Como lo hacía SIEMPRE igual, la ficha
              # se ajusta a lo que hace: lo que importa aquí es que se repita, y
              # pelearse con el modelo por cuál prenda es naranja solo consigue
              # que deje de repetirse.
              "wearing a grey work waistcoat over an orange long sleeve shirt, "
              "heavy work trousers",
              "Capataz de perforación, treinta años en el cinturón. Come lo mismo y a la misma "
              "hora desde siempre. Habla bajo y poco, pero cuando algo se tuerce en la galería "
              "es al primero al que llaman.", sexo="h"),
    # Sin gafas de soldar ni cuello alto en el retrato: con ellas el modelo le
    # puso las gafas sobre los ojos y una braga hasta la nariz, y un molde con la
    # cara tapada no le sirve a IP-Adapter para reconocer a nadie.
    # «pale dry lips» va escrito a propósito: sin eso, el modelo le pintaba los
    # labios de rosa fuerte, y IP-Adapter lo amplificaba en toda la hoja.
    # LA ROPA DE UN MOLDE TIENE QUE SER LISA. Es la regla más cara de las que hay
    # aquí, y se pagó entera con este personaje.
    #
    # Al pedir «open collar blue coverall» el modelo devolvía, siempre igual, una
    # camisa de RAYAS azules y blancas. Por la regla de «si lo repite, manda la
    # hoja» se le escribieron las rayas en la ficha. Y entonces TODOS sus planos
    # salieron con la habitación a rayas: las paredes, los armarios, la mesa, el
    # suelo. Cuatro tomas distintas, cuatro habitaciones a rayas.
    #
    # No era el adaptador de vestuario: se quitó y salió la MISMA imagen, píxel a
    # píxel. Era la propia hoja de personaje entrando por el adaptador de
    # identidad, que no sabe separar la cara de lo que la rodea y reparte por el
    # encuadre entero cualquier patrón que encuentre. Medido sobre las hojas:
    #
    #     óliver (chaleco liso)   textura  5,3
    #     suri   (abrigo liso)    textura  3,8
    #     teo    (rayas)          textura 12,9   <-- se come la sala
    #
    # («textura» = media de |diferencia entre píxeles contiguos en horizontal|.)
    #
    # Así que «manda la hoja» tiene un límite: manda mientras lo que haga no
    # estropee el plano. Con un patrón de alta frecuencia no se negocia; se
    # rehace el casting con una prenda lisa. Aquí, camiseta lisa.
    # Y un segundo aviso, del mismo personaje: «lisa» no puede ser lo ÚNICO que se
    # diga de la ropa. Al dejarle solo «camiseta lisa» desapareció del texto lo
    # que además de ropa decía «hombre» y «sitio de trabajo», y el casting devolvió
    # una mujer en ropa interior sobre una cama. La prenda tiene que ser lisa Y
    # seguir situando a la persona. Mono de trabajo, pero dicho «solid colour, no
    # pattern» para que no vuelva a interpretarlo como rayas.
    Personaje("teo", "Teo Marchal", "cliente",
              "portrait of a young man in his twenties, short dark hair, clean shaven, "
              "pale dry lips, plain charcoal grey work coverall, solid colour, no pattern, "
              "faint grease on one cheek, tired friendly look",
              "a young man in his twenties with short dark hair", 1033,
              "wearing a plain charcoal grey work coverall, solid colour, no pattern",
              "Técnico de atraque recién llegado, veinticuatro años. Todo le sorprende y "
              "pregunta de más. Come con el móvil en la mano y pide siempre lo más barato de "
              "la carta, que aún no cobra como los demás.", sexo="h"),
    # Clientas
    Personaje("nadia", "Nadia Ostrov", "cliente",
              "portrait of a weathered woman in her sixties, veteran miner, worn orange jumpsuit, "
              "short grey cropped hair, deep lines on her face, dust on the collar",
              "a woman in her sixties with short grey cropped hair and a weathered face", 1001,
              "wearing a worn orange work jumpsuit, dusty, zipped up to the chest",
              "Cuarenta años picando roca y una rodilla que se lo recuerda. Desayuna a las "
              "cinco y cena antes que nadie. No se fía de las pantallas: prefiere pedirle al "
              "camarero, que para eso está.", sexo="m"),
    Personaje("suri", "Suri Malabar", "cliente",
              "portrait of a woman in her thirties, geologist, green thermal jacket, long dark "
              "braid over one shoulder, rimless glasses, calm attentive look",
              "a woman in her thirties with dark shoulder length hair and glasses", 1003,
              # Ni trenza ni gafas sin montura: la hoja tiene melena corta a la
              # altura del hombro y unas gafas de pasta. Pedir la trenza en el
              # texto mientras la referencia enseñaba melena era la razón de que
              # sus planos se fueran a otro sitio -un café de madera en vez de la
              # cantina- y de que posara como en un catálogo.
              "wearing an olive green wool coat over a white shirt, dark trousers",
              "Geóloga de turno largo, llegó en el último carguero. Lo anota todo en la "
              "tableta, hasta lo que cena. Educada y algo distante; pide siempre lo mismo y "
              "paga desde la app sin levantar la vista.", sexo="m"),
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
                    # Vacío en las biblias descargadas antes de que `descargar()`
                    # lo trajera; quien lo use tiene que saber apañarse sin él.
                    "estacion": p.get("estacion") or "",
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
    estaciones: dict[int, str] = {}
    try:
        cabecera = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{url}/api/plano", headers=cabecera, timeout=20)
        r.raise_for_status()
        plano = r.json()["elementos"]

        # A qué sección de cocina va cada plato. No sale en la carta pública —que
        # es «sin estación, sin bajas y sin nada interno»— pero sí en la del
        # personal, y aprovechamos que el token ya está en la mano.
        #
        # Hace falta porque el escaparate repartía las comandas por estaciones al
        # azar, y el plano del KDS dice en voz alta «la comanda entra en cocina
        # REPARTIDA POR ESTACIONES». Salía una cerveza en la freidora y una brasa
        # en la barra: el plano desmentía su propia narración. El dato existe y es
        # una columna de `productos`, así que no hay que inventarlo.
        try:
            r = requests.get(f"{url}/api/catalogo", headers=cabecera, timeout=20)
            if r.ok:
                estaciones = {p["id"]: p["estacion"]
                              for c in r.json() for p in c.get("productos", [])
                              if p.get("estacion")}
        except Exception:
            pass
    finally:
        _logout(url, token)

    r = requests.get(f"{url}/api/publico/carta", timeout=20)
    r.raise_for_status()
    carta = r.json()
    for c in carta:
        for p in c.get("productos", []):
            if p["id"] in estaciones:
                p["estacion"] = estaciones[p["id"]]

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
