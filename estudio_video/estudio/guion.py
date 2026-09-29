"""Del prompt al guion: una frase suelta se convierte en escenas con vocabulario cerrado.

La interfaz pide una sola cosa: una frase. «Un cliente llega, pide desde el móvil
y paga con la app». De ahí tiene que salir algo que el resto del estudio pueda
ejecutar sin margen de invención.

La regla es que el guion **solo puede nombrar lo que existe**: las nueve cámaras
de la biblia, las nueve personas del elenco, las pantallas reales del KDS y los
platos de la carta. Si el modelo de lenguaje propone «la terraza con vistas al
mar», se descarta y se cae en la cámara más parecida. Un guion nunca inventa
decorado, porque el decorado es lo único que no se negocia.

Hay dos guionistas y el segundo no es un adorno:

  · **Con LLM** (Pyros o el que haya en `localhost:1234`): entiende la frase y
    reparte las escenas con criterio.
  · **Sin LLM**: plantillas por palabra clave. Menos fino, pero el estudio sigue
    funcionando con Pyros apagado, que pasa. Un generador que depende de que
    otra máquina esté encendida no es un generador, es una promesa.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

import requests

from . import biblia as B

LLM_URL = "http://localhost:1234/v1/chat/completions"
LLM_MODELO = "gemma-4-12b-it-mlx"
LLM_TIEMPO = 120

SEGUNDOS_MIN, SEGUNDOS_MAX = 2, 8
ESCENAS_MAX = 12


@dataclass
class Escena:
    camara: str
    accion: str                       # en inglés: va al modelo de imagen
    narracion: str = ""               # en español: va a Piper y a los subtítulos
    personajes: list[str] = field(default_factory=list)
    segundos: int = 4
    rotulo: str = ""
    pantalla: str | None = None       # clave de B.PANTALLAS: se graba de verdad
    pantalla_como: str = "inserto"    # inserto (esquina) | completa

    def semilla(self, base: int, indice: int) -> int:
        """Semilla reproducible: el mismo guion da el mismo vídeo, siempre."""
        crudo = f"{self.camara}|{self.accion}|{indice}"
        return (base + sum(ord(c) * (i + 1) for i, c in enumerate(crudo))) % (2**31)


@dataclass
class Guion:
    titulo: str
    tipo: str                          # tutorial | escena
    escenas: list[Escena]
    prompt: str = ""
    avisos: list[str] = field(default_factory=list)

    @property
    def segundos(self) -> int:
        return sum(e.segundos for e in self.escenas)

    def a_dict(self) -> dict:
        d = asdict(self)
        d["segundos"] = self.segundos
        return d

    @staticmethod
    def de_dict(d: dict) -> "Guion":
        return Guion(
            titulo=d["titulo"], tipo=d.get("tipo", "escena"),
            escenas=[Escena(**e) for e in d["escenas"]],
            prompt=d.get("prompt", ""), avisos=d.get("avisos", []),
        )


# ── Normalización ───────────────────────────────────────────────────────────
def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def _parecido(pedido: str, validos: list[str]) -> str | None:
    """La clave válida más parecida, o None. Sin dependencias: prefijo y contención."""
    p = _sin_tildes(pedido).strip()
    if p in validos:
        return p
    for v in validos:
        if p.startswith(v) or v.startswith(p) or v in p or p in v:
            return v
    return None


# ── Guionista con modelo de lenguaje ────────────────────────────────────────
def _instrucciones(bib: B.Biblia) -> str:
    camaras = "\n".join(f"  - {c.clave}: {c.nombre}. {c.nota}" for c in B.CAMARAS.values())
    gente = "\n".join(f"  - {p.clave}: {p.nombre}, {p.papel}" for p in B.ELENCO.values())
    pantallas = "\n".join(f"  - {k}: {v[2]}" for k, v in B.PANTALLAS.items())
    platos = ", ".join(f"{p['nombre']} ({p['precio']:.2f} €)" for p in bib.platos[:18])
    return f"""Eres el guionista de un estudio que hace vídeos cortos de una cantina
llamada Cantina Vesta-9, dentro de una estación minera excavada en un asteroide.
Los vídeos sirven para enseñar a usar su sistema de comandas (KDS+TPV) y para
mostrar a los clientes comiendo, pidiendo desde el móvil y pagando con la app.

Devuelve SOLO un JSON con esta forma, sin texto alrededor y sin markdown:

{{"titulo": "...", "tipo": "tutorial|escena", "escenas": [
  {{"camara": "<clave>", "accion": "<en INGLÉS, lo que se ve>",
    "narracion": "<en español, una frase que se lee en voz alta>",
    "personajes": ["<clave>"], "segundos": 4,
    "rotulo": "<opcional, texto corto en pantalla>",
    "pantalla": null o "<clave de pantalla>", "pantalla_como": "inserto|completa"}}
]}}

REGLAS QUE NO PUEDES SALTARTE:
1. `camara` SOLO puede ser una de estas claves:
{camaras}
2. `personajes` SOLO pueden ser estas claves:
{gente}
3. `pantalla` SOLO puede ser null o una de estas claves. Ponla cuando la escena
   tenga que ENSEÑAR la interfaz: entonces se graba la pantalla de verdad, no se
   dibuja. Un tutorial lleva pantalla en casi todas las escenas.
{pantallas}
4. `accion` va en inglés y describe SOLO personas y objetos: qué hacen, cómo se
   mueven, qué miran. NO describas la sala, ni los muros, ni la luz, ni el
   estilo: eso lo pone el estudio y es siempre igual.
5. `accion` NUNCA pide texto, letras, carteles, números ni pantallas legibles.
   Si hace falta enseñar la carta o un precio, se usa `pantalla`.
6. Entre 2 y {ESCENAS_MAX} escenas. Cada una entre {SEGUNDOS_MIN} y {SEGUNDOS_MAX} segundos.
7. La narración va en español de España, en frases cortas y llanas, sin
   exclamaciones ni lenguaje de anuncio.

Platos que existen en la carta (por si los nombras en la narración): {platos}.
"""


def modelo_a_usar(url: str = LLM_URL, preferido: str = LLM_MODELO) -> str | None:
    """El modelo preferido si está, y si no, cualquiera que sirva.

    LM Studio carga y descarga modelos según lo que haga cada uno en esta
    máquina, así que pedir siempre el mismo nombre falla el día que alguien lo
    descarga —pasó en cuanto se liberó la GPU— y el guionista se caía a
    plantillas diciendo solo «HTTPError», que no explica nada.
    """
    try:
        r = requests.get(url.replace("/chat/completions", "/models"), timeout=8)
        r.raise_for_status()
        ids = [m.get("id", "") for m in r.json().get("data", [])]
    except Exception:
        return None
    if preferido in ids:
        return preferido
    # Los de embeddings no saben conversar; el resto vale.
    utiles = [i for i in ids if "embed" not in i.lower()]
    return utiles[0] if utiles else None


def _pedir_al_llm(prompt: str, bib: B.Biblia, url: str = LLM_URL,
                  modelo: str | None = None) -> dict | None:
    modelo = modelo or modelo_a_usar(url)
    if not modelo:
        raise RuntimeError("no hay ningún modelo de lenguaje cargado en LM Studio")
    cuerpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": _instrucciones(bib)},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 2200,
    }
    r = requests.post(url, json=cuerpo, timeout=LLM_TIEMPO)
    r.raise_for_status()
    texto = r.json()["choices"][0]["message"]["content"]
    # Los modelos locales envuelven el JSON en ```json a la mínima.
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return None
    return json.loads(m.group(0))


# ── Guionista de plantillas (sin LLM) ───────────────────────────────────────
# Cada patrón es una escena ya montada. No pretende ser listo: pretende estar.
_PLANTILLAS: dict[str, dict] = {
    "llegada": {
        "palabras": ["llega", "entra", "viene", "llegan", "entran", "recibir", "bienvenid"],
        "escenas": [
            dict(camara="entrada", accion="two people walk in through the doorway, shaking dust "
                 "off their sleeves, looking around for a free table",
                 narracion="Llegan dos clientes y buscan mesa.",
                 personajes=["nadia", "teo"], segundos=4),
            dict(camara="comedor", accion="a waiter walks over to the newcomers and gestures "
                 "towards a free table, holding a rugged tablet",
                 narracion="El camarero les acomoda y abre la mesa en el TPV.",
                 personajes=["oliver", "nadia", "teo"], segundos=4),
            dict(camara="atraque", accion="", narracion="La mesa queda abierta con sus comensales.",
                 pantalla="tpv", pantalla_como="completa", segundos=5),
        ],
    },
    "pedir_movil": {
        "palabras": ["movil", "móvil", "app", "qr", "pide", "pedir", "carta", "aplicacion"],
        "escenas": [
            dict(camara="mesa", accion="a seated customer holds up a phone towards a small screen "
                 "on the table edge, then looks down at the phone and taps it",
                 narracion="El cliente lee el código de la mesa con el móvil.",
                 personajes=["suri"], segundos=4),
            dict(camara="mesa", accion="", narracion="La carta se abre en su teléfono, con los "
                 "alérgenos de cada plato.",
                 pantalla="cliente", pantalla_como="completa", segundos=6),
            # Sin personaje del elenco: en cocina no hay molde todavía, así que la
            # figura la pone el modelo y puede cambiar de una toma a otra.
            dict(camara="pase", accion="a cook places a finished plate under the warming lamps "
                 "and taps a screen, seen from behind",
                 narracion="El pedido entra directo en cocina.",
                 personajes=[], segundos=4),
        ],
    },
    "servir": {
        "palabras": ["sirve", "servir", "servido", "camarer", "plato", "come", "comer", "bandeja"],
        "escenas": [
            dict(camara="pase", accion="a cook slides a tray of plates onto the pass and rings "
                 "a bell, seen from behind",
                 narracion="Cocina termina y lo deja en el pase.",
                 personajes=[], segundos=4),
            dict(camara="comedor", accion="a waiter carries a tray of plates between the tables "
                 "and sets them down in front of two seated customers",
                 narracion="Sala recoge la bandeja y la lleva a la mesa.",
                 personajes=["oliver", "nadia", "teo"], segundos=5),
            dict(camara="mesa", accion="two seated customers start eating, steam rising from the plates",
                 narracion="Al entregar, el camarero confirma la entrega en su pantalla.",
                 personajes=["nadia", "teo"], segundos=4),
        ],
    },
    "pagar": {
        "palabras": ["paga", "pagar", "cuenta", "cobro", "cobrar", "factura", "bizum", "tarjeta"],
        "escenas": [
            dict(camara="mesa", accion="a seated customer taps a phone a few times and then sets "
                 "it down on the table, relaxed",
                 narracion="La clienta pide la cuenta desde la app y paga.",
                 personajes=["suri"], segundos=4),
            dict(camara="atraque", accion="a waiter at the counter glances at a screen and nods",
                 narracion="En la barra se ve el cobro entrar.",
                 personajes=["oliver"], segundos=4),
            dict(camara="atraque", accion="", narracion="La mesa queda libre y la factura, emitida.",
                 pantalla="tpv", pantalla_como="completa", segundos=5),
        ],
    },
    "cocina": {
        "palabras": ["cocina", "kds", "comanda", "fuego", "plancha", "freidora", "bump"],
        "escenas": [
            dict(camara="cocina", accion="a cook works at a hot plate, flames flaring, reaching "
                 "for a ticket screen above the counter, seen from behind",
                 narracion="En cocina, cada comanda aparece en su estación.",
                 personajes=[], segundos=4),
            dict(camara="cocina", accion="", narracion="Cocina termina en «lista»: quien la lleva a "
                 "la mesa es sala.",
                 pantalla="kds", pantalla_como="completa", segundos=6),
        ],
    },
}

_POR_DEFECTO = [
    dict(camara="comedor", accion="customers eating and talking at the tables, a waiter walking "
         "between them with a tray",
         narracion="Un servicio normal en la Cantina Vesta-9.",
         personajes=["nadia", "teo", "oliver"], segundos=5),
    dict(camara="atraque", accion="a waiter behind the counter serves a drink to a standing customer",
         narracion="En el atraque se despacha lo de paso.",
         personajes=["oliver", "klaus"], segundos=4),
]


def _por_plantillas(prompt: str) -> tuple[list[dict], list[str]]:
    p = _sin_tildes(prompt)
    elegidas: list[dict] = []
    usadas: list[str] = []
    for clave, plantilla in _PLANTILLAS.items():
        if any(w in p for w in plantilla["palabras"]):
            elegidas.extend(plantilla["escenas"])
            usadas.append(clave)
    if not elegidas:
        elegidas = list(_POR_DEFECTO)
        usadas.append("general")
    return elegidas, usadas


# ── Validación: aquí es donde se cierra el vocabulario ──────────────────────
def validar(crudo: dict, bib: B.Biblia, prompt: str) -> Guion:
    avisos: list[str] = []
    camaras = list(B.CAMARAS)
    gente = list(B.ELENCO)
    pantallas = list(B.PANTALLAS)

    escenas: list[Escena] = []
    for i, e in enumerate(crudo.get("escenas", [])[:ESCENAS_MAX]):
        cam = _parecido(str(e.get("camara", "")), camaras)
        if cam is None:
            cam = "comedor"
            avisos.append(f"Escena {i+1}: cámara «{e.get('camara')}» no existe; se usa «comedor».")

        pantalla = e.get("pantalla")
        if pantalla:
            pan = _parecido(str(pantalla), pantallas)
            if pan is None:
                avisos.append(f"Escena {i+1}: pantalla «{pantalla}» no existe; se quita.")
            pantalla = pan
        else:
            pantalla = None

        personajes = []
        for c in e.get("personajes") or []:
            clave = _parecido(str(c), gente)
            if clave is None:
                avisos.append(f"Escena {i+1}: «{c}» no está en el elenco; se ignora.")
                continue
            if clave not in personajes:
                personajes.append(clave)

        try:
            seg = int(e.get("segundos", 4))
        except (TypeError, ValueError):
            seg = 4
        seg = max(SEGUNDOS_MIN, min(SEGUNDOS_MAX, seg))

        accion = str(e.get("accion") or "").strip()
        # Cinturón: aunque las instrucciones lo prohíban, los modelos piden
        # carteles y menús legibles, y eso en SD1.5 sale como garabato.
        for prohibido in ("menu board", "sign", "signage", "text", "letters", "written",
                          "chalkboard", "price tag", "receipt", "label"):
            if prohibido in accion.lower():
                accion = re.sub(rf"\b{prohibido}\w*\b", "surface", accion, flags=re.I)
                avisos.append(f"Escena {i+1}: se quitó «{prohibido}» de la acción "
                              "(el modelo no sabe escribir; el texto va por pantalla real).")

        if not accion and not pantalla:
            avisos.append(f"Escena {i+1}: sin acción ni pantalla; se descarta.")
            continue

        escenas.append(Escena(
            camara=cam, accion=accion,
            narracion=str(e.get("narracion") or "").strip(),
            personajes=personajes, segundos=seg,
            rotulo=str(e.get("rotulo") or "").strip(),
            pantalla=pantalla,
            pantalla_como=("completa" if str(e.get("pantalla_como", "")).startswith("comp")
                           else "inserto"),
        ))

    if not escenas:
        avisos.append("El guion salió vacío; se usa el de por defecto.")
        escenas = [Escena(**e) for e in _POR_DEFECTO]

    titulo = str(crudo.get("titulo") or prompt[:60] or "Sin título").strip()
    tipo = "tutorial" if str(crudo.get("tipo", "")).startswith("tut") else "escena"
    return Guion(titulo=titulo, tipo=tipo, escenas=escenas, prompt=prompt, avisos=avisos)


def _repartir(escenas: list[dict], elegidos: list[str]) -> list[dict]:
    """Pone a los elegidos en las escenas que llevan gente, en orden.

    Los elegidos vienen de las caras que se pulsan en la web. Si alguien se
    molesta en decir «quiero a Nadia y a Klaus», salen Nadia y Klaus, no los que
    trajera la plantilla. Las escenas sin gente (una pantalla, una toma de
    cocina de espaldas) se quedan como están.
    """
    if not elegidos:
        return escenas
    fuera = []
    turno = 0
    for e in escenas:
        e = dict(e)
        cuantos = len(e.get("personajes") or [])
        if cuantos:
            e["personajes"] = [elegidos[(turno + n) % len(elegidos)] for n in range(cuantos)]
            # Sin repetir a nadie dentro del mismo plano.
            vistos, limpio = set(), []
            for c in e["personajes"]:
                if c not in vistos:
                    vistos.add(c)
                    limpio.append(c)
            e["personajes"] = limpio
            turno += 1
        fuera.append(e)
    return fuera


def escribir(prompt: str, bib: B.Biblia | None = None, usar_llm: bool = True,
             elegidos: list[str] | None = None) -> Guion:
    """El guion de un prompt. Intenta el LLM; si no hay, tira de plantillas.

    `elegidos` son las claves del elenco que el usuario ha pulsado en la web:
    esas son las personas que salen, y nadie más.
    """
    bib = bib or B.cargar()
    avisos: list[str] = []
    elegidos = [c for c in (elegidos or []) if c in B.ELENCO]

    if usar_llm:
        try:
            extra = ""
            if elegidos:
                quienes = ", ".join(f"{c} ({B.ELENCO[c].nombre})" for c in elegidos)
                extra = ("\n\nEn este vídeo salen EXACTAMENTE estas personas y ninguna otra: "
                         f"{quienes}. Reparte sus intervenciones entre las escenas.")
            crudo = _pedir_al_llm(prompt + extra, bib)
            if crudo:
                g = validar(crudo, bib, prompt)
                if elegidos:
                    sobran = {c for e in g.escenas for c in e.personajes} - set(elegidos)
                    for e in g.escenas:
                        e.personajes = [c for c in e.personajes if c in elegidos]
                    if sobran:
                        avisos.append("Se quitaron personas que no habías elegido: "
                                      + ", ".join(sorted(sobran)) + ".")
                g.avisos = avisos + g.avisos
                return g
            avisos.append("El modelo de lenguaje no devolvió JSON; se usan plantillas.")
        except Exception as e:
            avisos.append(f"Sin modelo de lenguaje ({type(e).__name__}); se usan plantillas.")

    escenas, usadas = _por_plantillas(prompt)
    escenas = _repartir(escenas, elegidos)
    tipo = "tutorial" if any(w in _sin_tildes(prompt) for w in ("tutorial", "como se", "explica",
                                                               "enseña", "ensena", "aprende")) else "escena"
    crudo: dict[str, Any] = {"titulo": prompt[:60] or "Cantina Vesta-9", "tipo": tipo,
                             "escenas": escenas}
    g = validar(crudo, bib, prompt)
    g.avisos = avisos + [f"Guion por plantillas ({', '.join(usadas)})."] + g.avisos
    return g


def hay_llm(url: str = LLM_URL) -> bool:
    try:
        return requests.get(url.replace("/chat/completions", "/models"), timeout=4).ok
    except Exception:
        return False
