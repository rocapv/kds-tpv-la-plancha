"""Lectura de imágenes con un modelo de visión (albaranes, por ahora).

La cadena está copiada en lo esencial de un sistema que ya lleva meses en producción en otro
proyecto de la casa, porque sus decisiones están pagadas con errores reales:

  · **temperatura 0 y esquema JSON**: la respuesta es un objeto validable, no prosa.
  · **el modelo transcribe, no calcula**: los totales los echa el código. Un modelo que suma
    se equivoca en silencio, y en un albarán eso es dinero.
  · **saneado hostil**: se busca el primer objeto JSON de la respuesta, se quitan las vallas de
    código y se comprueba cada campo. Lo que no encaje, fuera.
  · **caché por sha256**: la misma foto dos veces no se paga dos veces.
  · **precheck barato**: dimensiones y tamaño antes de enviar nada por la red.

El proveedor es cualquier servidor con la API de OpenAI (LM Studio en la GPU de Pecera, por
defecto). No hace falta nube ni clave: si el servidor no responde, se dice y se acabó.
"""
import base64
import io as _io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .db import q1

LADO_MAXIMO = 1600          # más resolución no mejora la lectura y multiplica el tiempo
TOKENS_MAXIMOS = 3000       # con menos, un modelo que razona se queda sin sitio y devuelve vacío
ESPERA_S = 240


def ajuste(clave: str, por_defecto: str) -> str:
    fila = q1("SELECT valor FROM ajustes WHERE clave=%s", (clave,))
    return (fila["valor"] if fila else por_defecto) or por_defecto


# ─────────────── Preparación de la imagen ───────────────
def preparar(ruta: Path) -> tuple[str, int, int]:
    """Devuelve la imagen en base64, reescalada, y sus dimensiones originales.

    Se reescala en el servidor y no en el móvil: el teléfono manda lo que quiere, y aquí es
    donde se controla lo que acaba viajando al modelo.
    """
    try:
        from PIL import Image
    except ImportError:                      # sin Pillow se manda tal cual, pero se avisa
        datos = ruta.read_bytes()
        return base64.b64encode(datos).decode(), 0, 0

    with Image.open(ruta) as img:
        ancho, alto = img.size
        img = img.convert("RGB")
        if max(ancho, alto) > LADO_MAXIMO:
            escala = LADO_MAXIMO / max(ancho, alto)
            img = img.resize((int(ancho * escala), int(alto * escala)), Image.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode(), ancho, alto


# ─────────────── Conversación con el modelo ───────────────
ESQUEMA_ALBARAN = {
    "type": "object",
    "properties": {
        "es_albaran": {"type": "boolean"},
        "proveedor": {"type": ["string", "null"]},
        "numero": {"type": ["string", "null"]},
        "fecha": {"type": ["string", "null"], "description": "AAAA-MM-DD"},
        "total_texto": {"type": ["string", "null"], "description": "el total tal y como aparece"},
        "lineas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "descripcion": {"type": "string"},
                    "cantidad": {"type": ["number", "null"]},
                    "unidad": {"type": ["string", "null"]},
                    "precio_texto": {"type": ["string", "null"]},
                    "importe_texto": {"type": ["string", "null"]},
                },
                "required": ["descripcion"],
            },
        },
    },
    "required": ["es_albaran", "lineas"],
}

INSTRUCCIONES = """Eres un lector de albaranes de un restaurante. Mira la imagen y devuelve SOLO un objeto JSON.

Reglas, por orden de importancia:
1. Primero decide qué es: si la imagen NO es un albarán, una factura o un ticket de compra,
   devuelve {"es_albaran": false, "lineas": []} y nada más.
2. TRANSCRIBE, no interpretes. Los textos, tal y como están escritos en el papel, con sus
   abreviaturas. No traduzcas, no corrijas y no completes lo que no se lee.
3. NO CALCULES NADA. No sumes, no multipliques, no deduzcas precios. Los importes se copian
   como texto en "precio_texto" e "importe_texto"; de las cuentas se encarga otro.
4. Si un dato no se ve o no estás seguro, pon null. Es preferible un hueco a un invento.
5. La fecha, en formato AAAA-MM-DD si se puede deducir sin ambigüedad; si no, null."""


def _sanear(texto: str) -> dict:
    """Extrae el primer objeto JSON de la respuesta, venga como venga."""
    if not texto:
        raise ValueError("el modelo devolvió una respuesta vacía")
    limpio = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        pass
    inicio = limpio.find("{")
    if inicio == -1:
        raise ValueError(f"no hay JSON en la respuesta: {limpio[:120]}")
    profundidad, dentro_texto, escapado = 0, False, False
    for i, ch in enumerate(limpio[inicio:], inicio):
        if dentro_texto:
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif ch == '"':
                dentro_texto = False
            continue
        if ch == '"':
            dentro_texto = True
        elif ch == "{":
            profundidad += 1
        elif ch == "}":
            profundidad -= 1
            if profundidad == 0:
                return json.loads(limpio[inicio:i + 1])
    raise ValueError("el JSON de la respuesta está incompleto")


def leer_albaran(ruta: Path) -> dict:
    """Manda la imagen al modelo y devuelve {datos, modelo, ms}. Lanza excepción si no puede."""
    url = ajuste("vision_url", "http://192.168.1.69:1234/v1").rstrip("/")
    modelo = ajuste("vision_modelo", "google/gemma-4-12b-qat")
    b64, _, _ = preparar(ruta)

    cuerpo = {
        "model": modelo,
        "temperature": 0,
        "max_tokens": TOKENS_MAXIMOS,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": INSTRUCCIONES},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
        ]}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "albaran", "strict": False, "schema": ESQUEMA_ALBARAN}},
    }
    peticion = urllib.request.Request(url + "/chat/completions", method="POST",
                                      data=json.dumps(cuerpo).encode(),
                                      headers={"Content-Type": "application/json"})
    arranque = time.time()
    try:
        with urllib.request.urlopen(peticion, timeout=ESPERA_S) as r:
            respuesta = json.loads(r.read())
    except urllib.error.URLError as e:
        raise RuntimeError(f"no se puede hablar con el modelo de visión ({url}): {e.reason}")
    ms = int((time.time() - arranque) * 1000)

    eleccion = respuesta["choices"][0]
    datos = _sanear(eleccion["message"].get("content") or "")
    if eleccion.get("finish_reason") == "length" and not datos.get("lineas"):
        raise RuntimeError("el modelo se quedó sin espacio antes de contestar; sube max_tokens")
    return {"datos": datos, "modelo": modelo, "ms": ms}


# ─────────────── Del texto del papel a números ───────────────
def a_centimos(texto) -> int | None:
    """«12,50 €», «12.50», «1.234,56» → céntimos. Devuelve None si no hay un número claro.

    Aquí es donde se decide si una coma es decimal o separador de miles, que es justo el tipo
    de decisión que un modelo de lenguaje no debe tomar.
    """
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return int(round(float(texto) * 100))
    limpio = re.sub(r"[^\d,.\-]", "", str(texto)).strip()
    if not limpio:
        return None
    if "," in limpio and "." in limpio:                       # el último separador manda
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        return int(round(float(limpio) * 100))
    except ValueError:
        return None


def parecido(a: str, b: str) -> int:
    """0-100. Compara nombres normalizados, y premia que uno contenga al otro."""
    import unicodedata
    from difflib import SequenceMatcher

    def limpiar(t):
        t = unicodedata.normalize("NFKD", (t or "").lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9 ]", " ", t).split()

    pa, pb = limpiar(a), limpiar(b)
    if not pa or not pb:
        return 0
    base = SequenceMatcher(None, " ".join(pa), " ".join(pb)).ratio() * 100
    comunes = len(set(pa) & set(pb)) / max(len(set(pa)), len(set(pb))) * 100
    return int(round(max(base, comunes)))
