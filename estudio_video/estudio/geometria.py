"""De las milésimas del plano a los mapas que atan al modelo a esta sala.

El plano del KDS es una lista de rectángulos vistos desde arriba. Aquí se
levantan en 3D —cada tipo con su altura—, se mira la sala desde una cámara fija
y se sacan dos imágenes:

  · **profundidad** (`*_profundidad.png`): cerca claro, lejos oscuro. Es lo que
    come ControlNet depth, y es lo que impide que el modelo mueva un muro o se
    invente una sala más grande.
  · **líneas** (`*_lineas.png`): las aristas visibles. Segundo control opcional,
    útil cuando la profundidad sola deja el encuadre demasiado suelto.

Un rasterizador propio de cuarenta cajas no necesita OpenGL ni una librería de
3D: son cuatro matrices y un z-buffer de numpy. Lo importante no es que sea
bonito —nadie va a ver estas imágenes— sino que sea SIEMPRE EL MISMO. Por eso no
hay nada aleatorio aquí dentro.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from . import biblia as B

CERCA = 0.12          # plano de recorte: lo que esté más cerca que esto, se corta
ARRIBA = np.array([0.0, 0.0, 1.0])     # en este sistema z es la altura


# ── Cajas ───────────────────────────────────────────────────────────────────
ASIENTO = 0.45         # altura del asiento
RESPALDO = 0.92        # altura del respaldo
SILLA = 0.42           # lado de la silla
HUECO_SILLA = 0.30     # cuánto se separa del borde de la mesa


def _sillas(cx: float, cy: float, rx: float, ry: float, circular: bool) -> list[dict]:
    """Las sillas de una mesa, deducidas de la propia mesa.

    En el plano del KDS no hay sillas: hay mesas. Pero un vídeo de clientes
    comiendo necesita sillas, y si no se las damos nosotros el modelo se las
    inventa distintas en cada toma, que es exactamente lo que se quería evitar.
    Se derivan de la mesa con una regla fija —cuatro alrededor de una redonda,
    dos taburetes en las de la barra—, así que son las mismas siempre.
    """
    mitad = SILLA / 2
    if circular:
        sitios = [(cx, cy - ry - HUECO_SILLA - mitad), (cx, cy + ry + HUECO_SILLA + mitad),
                  (cx - rx - HUECO_SILLA - mitad, cy), (cx + rx + HUECO_SILLA + mitad, cy)]
    else:
        sitios = [(cx - rx * 0.5, cy + ry + HUECO_SILLA + mitad),
                  (cx + rx * 0.5, cy + ry + HUECO_SILLA + mitad)]

    out = []
    for sx, sy in sitios:
        out.append({"nombre": "Silla", "tipo": "silla",
                    "min": (sx - mitad, sy - mitad, ASIENTO - 0.06),
                    "max": (sx + mitad, sy + mitad, ASIENTO)})
        out.append({"nombre": "Silla (pata)", "tipo": "silla",
                    "min": (sx - mitad * 0.35, sy - mitad * 0.35, 0.0),
                    "max": (sx + mitad * 0.35, sy + mitad * 0.35, ASIENTO - 0.06)})
        if circular:          # respaldo en el lado que da la espalda a la mesa
            dx, dy = sx - cx, sy - cy
            if abs(dx) > abs(dy):
                x = sx + mitad * (1 if dx > 0 else -1)
                out.append({"nombre": "Silla (respaldo)", "tipo": "silla",
                            "min": (x - 0.05, sy - mitad, ASIENTO),
                            "max": (x + 0.05, sy + mitad, RESPALDO)})
            else:
                y = sy + mitad * (1 if dy > 0 else -1)
                out.append({"nombre": "Silla (respaldo)", "tipo": "silla",
                            "min": (sx - mitad, y - 0.05, ASIENTO),
                            "max": (sx + mitad, y + 0.05, RESPALDO)})
    return out


def cajas_de(bib: B.Biblia, sin_techo: bool = False) -> list[dict]:
    """El local en cajas, en metros. Incluye suelo, techo y las sillas deducidas.

    Las mesas redondas se aproximan con un prisma de 16 lados: a la resolución a
    la que trabaja ControlNet, la diferencia con un cilindro no existe, y evita
    escribir un rasterizador de superficies curvas para nada.
    """
    piezas: list[dict] = []

    lado = B.LADO_METROS
    piezas.append({"nombre": "Suelo", "tipo": "suelo",
                   "min": (0.0, 0.0, -0.05), "max": (lado, lado, 0.0)})
    if not sin_techo:
        piezas.append({"nombre": "Techo", "tipo": "techo",
                       "min": (0.0, 0.0, B.ALTURA_TECHO), "max": (lado, lado, B.ALTURA_TECHO + 0.05)})

    for el in bib.plano:
        alto = B.altura_de(el)
        if alto <= 0:
            continue                    # las zonas son suelo pintado: no levantan
        x0 = B.a_metros(el["x"])
        y0 = B.a_metros(el["y"])
        x1 = x0 + B.a_metros(el["ancho"])
        y1 = y0 + B.a_metros(el["alto"])

        pieza = {"nombre": el["nombre"], "tipo": el["tipo"],
                 "min": (x0, y0, 0.0), "max": (x1, y1, alto)}

        if el["tipo"] == "mesa":
            # La mesa es tablero + pie: una caja sola parece un cubo y el modelo
            # pinta un bloque de piedra en vez de una mesa.
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
            if el["forma"] == "circ":
                piezas.append({"nombre": el["nombre"], "tipo": "mesa",
                               "prisma": (cx, cy, rx, ry, alto - 0.06, alto), "lados": 16})
            else:
                piezas.append({"nombre": el["nombre"], "tipo": "mesa",
                               "min": (x0, y0, alto - 0.06), "max": (x1, y1, alto)})
            piezas.append({"nombre": el["nombre"] + " (pie)", "tipo": "mesa",
                           "min": (cx - rx * 0.18, cy - ry * 0.18, 0.0),
                           "max": (cx + rx * 0.18, cy + ry * 0.18, alto - 0.06)})
            piezas.extend(_sillas(cx, cy, rx, ry, el["forma"] == "circ"))
            continue

        if el["tipo"] == "puerta":
            # Un hueco, no un bloque: se marca el dintel para que quede la
            # abertura y el modelo vea por dónde se entra.
            piezas.append({"nombre": el["nombre"], "tipo": "puerta",
                           "min": (x0, y0, alto), "max": (x1, y1, B.ALTURA_TECHO)})
            continue

        piezas.append(pieza)

    return piezas


def _triangulos(pieza: dict) -> list[np.ndarray]:
    """Las caras de una pieza, cada una como un polígono de vértices 3D."""
    if "prisma" in pieza:
        cx, cy, rx, ry, z0, z1 = pieza["prisma"]
        n = pieza.get("lados", 16)
        ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
        xs, ys = cx + rx * np.cos(ang), cy + ry * np.sin(ang)
        caras = [np.stack([xs, ys, np.full(n, z1)], axis=1),          # tapa
                 np.stack([xs[::-1], ys[::-1], np.full(n, z0)], axis=1)]
        for i in range(n):
            j = (i + 1) % n
            caras.append(np.array([[xs[i], ys[i], z0], [xs[j], ys[j], z0],
                                   [xs[j], ys[j], z1], [xs[i], ys[i], z1]]))
        return caras

    (x0, y0, z0), (x1, y1, z1) = pieza["min"], pieza["max"]
    v = {
        "abajo":    [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]],
        "arriba":   [[x0, y0, z1], [x0, y1, z1], [x1, y1, z1], [x1, y0, z1]],
        "norte":    [[x0, y0, z0], [x0, y0, z1], [x1, y0, z1], [x1, y0, z0]],
        "sur":      [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]],
        "oeste":    [[x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1]],
        "este":     [[x1, y0, z0], [x1, y0, z1], [x1, y1, z1], [x1, y1, z0]],
    }
    return [np.array(c, dtype=float) for c in v.values()]


def _aristas(pieza: dict) -> list[tuple[np.ndarray, np.ndarray]]:
    """Las aristas de una pieza, para el mapa de líneas."""
    if "prisma" in pieza:
        cx, cy, rx, ry, z0, z1 = pieza["prisma"]
        n = pieza.get("lados", 16)
        ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
        xs, ys = cx + rx * np.cos(ang), cy + ry * np.sin(ang)
        out = []
        for i in range(n):
            j = (i + 1) % n
            out.append((np.array([xs[i], ys[i], z1]), np.array([xs[j], ys[j], z1])))
            out.append((np.array([xs[i], ys[i], z0]), np.array([xs[j], ys[j], z0])))
            out.append((np.array([xs[i], ys[i], z0]), np.array([xs[i], ys[i], z1])))
        return out

    (x0, y0, z0), (x1, y1, z1) = pieza["min"], pieza["max"]
    p = [np.array([x, y, z]) for z in (z0, z1) for x, y in
         ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    pares = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7)]
    return [(p[a], p[b]) for a, b in pares]


# ── Cámara ──────────────────────────────────────────────────────────────────
class Vista:
    """Pasa de metros del local a píxeles de la imagen. Sin estado aleatorio."""

    def __init__(self, cam: B.Camara, ancho: int, alto: int):
        self.ancho, self.alto = ancho, alto
        pos = np.array(cam.pos, dtype=float)
        mira = np.array(cam.mira, dtype=float)
        adelante = mira - pos
        adelante /= np.linalg.norm(adelante)
        arriba_mundo = ARRIBA
        if abs(float(np.dot(adelante, arriba_mundo))) > 0.999:
            arriba_mundo = np.array([0.0, 1.0, 0.0])   # cenital: el «arriba» no puede ser el eje de mira
        derecha = np.cross(adelante, arriba_mundo)
        derecha /= np.linalg.norm(derecha)
        arriba = np.cross(derecha, adelante)
        self.pos = pos
        self.R = np.stack([derecha, arriba, adelante])     # filas
        self.f = 1.0 / math.tan(math.radians(cam.fov) / 2.0)
        self.aspecto = ancho / alto

    def a_camara(self, pts: np.ndarray) -> np.ndarray:
        return (pts - self.pos) @ self.R.T                 # (n,3): x derecha, y arriba, z hacia delante

    def a_pantalla(self, cam: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        z = np.maximum(cam[:, 2], 1e-6)
        ndc_x = (cam[:, 0] / z) * self.f / self.aspecto
        ndc_y = (cam[:, 1] / z) * self.f
        px = (ndc_x * 0.5 + 0.5) * self.ancho
        py = (0.5 - ndc_y * 0.5) * self.alto
        return np.stack([px, py], axis=1), z


def _recortar(cam: np.ndarray) -> np.ndarray:
    """Sutherland-Hodgman contra z = CERCA.

    Sin esto, un vértice detrás de la cámara se proyecta al otro lado y aparecen
    triángulos gigantes cruzando la imagen. Pasa siempre que la cámara está
    dentro de la sala, que es justo nuestro caso.
    """
    salida = []
    n = len(cam)
    for i in range(n):
        a, b = cam[i], cam[(i + 1) % n]
        da, db = a[2] - CERCA, b[2] - CERCA
        if da >= 0:
            salida.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            salida.append(a + (b - a) * t)
    return np.array(salida) if salida else np.empty((0, 3))


# ── Rasterizado ─────────────────────────────────────────────────────────────
def _pintar_triangulo(zbuf: np.ndarray, p: np.ndarray, z: np.ndarray) -> None:
    """Z-buffer de un triángulo, con 1/z interpolado (que es lo lineal en pantalla)."""
    alto, ancho = zbuf.shape
    minx = max(int(math.floor(p[:, 0].min())), 0)
    maxx = min(int(math.ceil(p[:, 0].max())), ancho - 1)
    miny = max(int(math.floor(p[:, 1].min())), 0)
    maxy = min(int(math.ceil(p[:, 1].max())), alto - 1)
    if minx > maxx or miny > maxy:
        return

    (x0, y0), (x1, y1), (x2, y2) = p
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(den) < 1e-9:
        return

    X, Y = np.meshgrid(np.arange(minx, maxx + 1) + 0.5,
                       np.arange(miny, maxy + 1) + 0.5)
    l0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
    l1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
    l2 = 1.0 - l0 - l1
    dentro = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
    if not dentro.any():
        return

    inv = l0 / z[0] + l1 / z[1] + l2 / z[2]
    with np.errstate(divide="ignore", invalid="ignore"):
        prof = 1.0 / inv
    trozo = zbuf[miny:maxy + 1, minx:maxx + 1]
    mejor = dentro & np.isfinite(prof) & (prof > 0) & (prof < trozo)
    zbuf[miny:maxy + 1, minx:maxx + 1] = np.where(mejor, prof, trozo)


def zbuffer(bib: B.Biblia, cam: B.Camara, ancho: int, alto: int) -> tuple[np.ndarray, Vista]:
    """El mapa de distancias en metros. Infinito donde no hay nada."""
    vista = Vista(cam, ancho, alto)
    zbuf = np.full((alto, ancho), np.inf)
    for pieza in cajas_de(bib, sin_techo=cam.sin_techo):
        for cara in _triangulos(pieza):
            en_cam = vista.a_camara(cara)
            recortada = _recortar(en_cam)
            if len(recortada) < 3:
                continue
            pix, z = vista.a_pantalla(recortada)
            for i in range(1, len(recortada) - 1):       # abanico
                _pintar_triangulo(zbuf,
                                  np.array([pix[0], pix[i], pix[i + 1]]),
                                  np.array([z[0], z[i], z[i + 1]]))
    return zbuf, vista


def mapa_profundidad(zbuf: np.ndarray) -> Image.Image:
    """Cerca blanco, lejos negro: el convenio que espera ControlNet depth.

    Se normaliza por **disparidad** (1/z), no por distancia. Los mapas con los
    que se entrenó ControlNet salen de MiDaS, que estima disparidad, y además
    reparte mucho mejor el gris: con distancia lineal, el suelo de los dos
    primeros metros se come medio rango y el fondo de la sala queda aplastado en
    un par de tonos.
    """
    finito = np.isfinite(zbuf)
    if not finito.any():
        return Image.new("L", (zbuf.shape[1], zbuf.shape[0]), 0)
    vistos = zbuf[finito]
    cerca = max(float(np.percentile(vistos, 1.0)), CERCA)
    lejos = float(np.percentile(vistos, 99.5))
    if lejos - cerca < 1e-6:
        lejos = cerca + 1.0
    z = np.clip(zbuf, cerca, lejos)
    d_cerca, d_lejos = 1.0 / cerca, 1.0 / lejos
    norm = (1.0 / z - d_lejos) / (d_cerca - d_lejos)
    norm[~finito] = 0.0
    mapa = Image.fromarray((np.clip(norm, 0, 1) * 255).astype(np.uint8), mode="L")

    # Un suavizado corto antes de entregarlo. Los mapas con los que se entrenó
    # ControlNet salen de fotos y son continuos; este sale de cajas rasterizadas
    # y tiene cantos de un píxel, durísimos. Esa dureza es parte de por qué, a
    # fuerza alta, las escenas salían saturadas y con textura de puntos. Con el
    # borde ablandado, la misma geometría guía igual y pelea menos.
    return mapa.filter(ImageFilter.GaussianBlur(radius=1.6))


def mapa_lineas(bib: B.Biblia, cam: B.Camara, zbuf: np.ndarray, vista: Vista,
                muestras: int = 160) -> Image.Image:
    """Aristas visibles, blancas sobre negro.

    La oclusión se resuelve con el z-buffer que ya está hecho: se camina la
    arista, y donde la distancia al ojo coincide con lo que hay pintado, la
    arista se ve; donde hay algo delante, no.
    """
    alto, ancho = zbuf.shape
    lienzo = np.zeros((alto, ancho), dtype=np.uint8)
    for pieza in cajas_de(bib, sin_techo=cam.sin_techo):
        if pieza["tipo"] in ("techo", "suelo"):
            continue
        for a, b in _aristas(pieza):
            t = np.linspace(0.0, 1.0, muestras)[:, None]
            pts = a * (1 - t) + b * t
            en_cam = vista.a_camara(pts)
            delante = en_cam[:, 2] > CERCA
            if not delante.any():
                continue
            pix, z = vista.a_pantalla(en_cam[delante])
            zz = z
            xs = np.round(pix[:, 0]).astype(int)
            ys = np.round(pix[:, 1]).astype(int)
            ok = (xs >= 0) & (xs < ancho) & (ys >= 0) & (ys < alto)
            if not ok.any():
                continue
            xs, ys, zz = xs[ok], ys[ok], zz[ok]
            # Tolerancia proporcional: a diez metros, un centímetro no decide nada.
            visible = zz <= zbuf[ys, xs] * 1.004 + 0.01
            lienzo[ys[visible], xs[visible]] = 255
    return Image.fromarray(lienzo, mode="L")


# Por debajo de esta cobertura, la cámara está mirando al vacío y ControlNet no
# tiene nada que sujetar: el modelo se va con la referencia de identidad y
# devuelve a la persona POSANDO en un sitio que no es la cantina, haga la fuerza
# que haga. Costó media tarde y una sospecha equivocada —se culpó a
# `FUERZA_PROFUNDIDAD` y se llegó a subirla, rompiendo todas las demás cámaras—
# antes de mirar el mapa y ver que estaba negro. Se avisa para no repetirlo.
#
# Medido: de las cámaras de interior, ninguna baja del 0,84 salvo `entrada`, que
# está en 0,44. Las que miran el edificio desde fuera (`sin_techo`) ven el
# exterior por definición y quedan exentas.
COBERTURA_MINIMA = 0.55


def cobertura_del_mapa(clave: str, destino: Path | None = None) -> float:
    """Qué parte del encuadre tiene geometría delante, de 0 a 1."""
    f = (destino or B.DIR_CONTROL) / f"{clave}_profundidad.png"
    if not f.exists():
        return 1.0
    return float((np.asarray(Image.open(f).convert("L")) > 8).mean())


def camara_vacia(clave: str, destino: Path | None = None) -> float | None:
    """La cobertura si la cámara mira demasiado vacío, o None si está bien."""
    cam = B.CAMARAS.get(clave)
    if cam is not None and cam.sin_techo:
        return None
    c = cobertura_del_mapa(clave, destino)
    return c if c < COBERTURA_MINIMA else None


def generar_controles(bib: B.Biblia | None = None, ancho: int | None = None,
                      alto: int | None = None, destino: Path | None = None) -> dict[str, dict]:
    """Los mapas de las nueve cámaras, de una vez. Devuelve dónde quedó cada cosa."""
    bib = bib or B.cargar()
    ancho = ancho or B.FORMATO["ancho"]
    alto = alto or B.FORMATO["alto"]
    destino = destino or B.DIR_CONTROL
    destino.mkdir(parents=True, exist_ok=True)

    hecho: dict[str, dict] = {}
    for clave, cam in B.CAMARAS.items():
        zbuf, vista = zbuffer(bib, cam, ancho, alto)
        prof = destino / f"{clave}_profundidad.png"
        lin = destino / f"{clave}_lineas.png"
        mapa_profundidad(zbuf).save(prof)
        mapa_lineas(bib, cam, zbuf, vista).save(lin)
        visto = np.isfinite(zbuf)
        hecho[clave] = {
            "camara": cam.nombre,
            "profundidad": str(prof),
            "lineas": str(lin),
            "cobertura": round(float(visto.mean()), 3),
            "metros_cerca": round(float(zbuf[visto].min()), 2) if visto.any() else None,
            "metros_lejos": round(float(zbuf[visto].max()), 2) if visto.any() else None,
        }
    return hecho
