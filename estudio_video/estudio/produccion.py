"""La producción: de un prompt a un MP4, pasando por todo lo demás.

Un trabajo es una carpeta en `trabajos/<id>/` con TODO dentro: el guion, los
clips, la voz, los subtítulos y el estado. Nada vive solo en memoria, así que se
puede cerrar la web, reiniciar Pecera o mirar qué pasó tres días después.

El orden importa y no es el obvio. Primero se graban las pantallas del KDS y se
hace la voz, que no gastan GPU; la generación de imagen va al final y de una en
una. Así, si la GPU está ocupada —cosa que pasa: la comparten los relatos, los
cursos y el pipeline de Star Citizen— lo que se pierde es solo la parte que de
verdad la necesitaba.
"""
from __future__ import annotations

import json
import shutil
import threading
import time
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from . import biblia as B
from . import comfy as C
from . import elenco as E
from . import geometria as G
from . import guion as Gu
from . import montaje as M
from . import pantallas as P
from . import publicar as Pub
from . import voz as V

DIR_TRABAJOS = B.RAIZ / "trabajos"
DIR_SALIDAS = B.RAIZ / "salidas"
VRAM_MINIMA = 5200        # MiB: por debajo de esto, SD1.5 + AnimateDiff no cabe


class Trabajo:
    """Una producción. Se guarda sola en disco cada vez que cambia de paso."""

    def __init__(self, ident: str):
        self.id = ident
        self.dir = DIR_TRABAJOS / ident
        self.dir.mkdir(parents=True, exist_ok=True)
        self.estado: dict = {
            "id": ident, "fase": "nuevo", "paso": "", "avance": 0.0,
            "creado": datetime.now().isoformat(timespec="seconds"),
            "prompt": "", "titulo": "", "avisos": [], "error": None,
            "salida": None, "portada": None, "srt": None, "escenas": [],
        }

    # ── estado ──────────────────────────────────────────────────────────
    @property
    def fichero_estado(self) -> Path:
        return self.dir / "estado.json"

    def guardar(self) -> None:
        self.fichero_estado.write_text(
            json.dumps(self.estado, ensure_ascii=False, indent=1), encoding="utf-8")

    def anotar(self, paso: str, avance: float | None = None) -> None:
        self.estado["paso"] = paso
        if avance is not None:
            self.estado["avance"] = round(max(0.0, min(1.0, avance)), 3)
        self.guardar()

    def avisar(self, texto: str) -> None:
        self.estado["avisos"].append(texto)
        self.guardar()

    @staticmethod
    def cargar(ident: str) -> dict | None:
        f = DIR_TRABAJOS / ident / "estado.json"
        if not f.exists():
            return None
        return json.loads(f.read_text(encoding="utf-8"))

    @staticmethod
    def listar() -> list[dict]:
        if not DIR_TRABAJOS.exists():
            return []
        out = []
        for d in sorted(DIR_TRABAJOS.iterdir(), reverse=True):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            e = Trabajo.cargar(d.name)
            if e:
                out.append(e)
        return out


def _nuevo_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def prompt_de(esc: "Gu.Escena") -> str:
    """El prompt positivo de un plano. **La acción va primero.**

    Vive aquí, y no copiado en cada script de prueba, por una razón aprendida a
    base de perder una tarde: `probar_fijo.py` montaba su propio grafo, más
    simple, y el estudio se estuvo ajustando con un instrumento que no medía lo
    que luego se ejecutaba. Un prompt construido en dos sitios acaba siendo dos
    prompts distintos.

    El orden fue justo el contrario —QUIÉN, QUÉ LLEVA PUESTO, qué hace, ambiente—
    y tenía su motivo: sin la persona delante, el decorado se comía el prompt y
    la gente no llegaba a aparecer. Eso era verdad **antes de que existieran los
    dos IP-Adapter**. Ahora la cara la pone la hoja de personaje y la ropa la
    pone el adaptador de vestuario, las dos en el espacio de imagen, así que
    gastar en describirlas más de la mitad de los 77 tokens de CLIP no añade
    nada: solo empuja la acción al centro del prompt, donde se diluye. Y la
    acción es lo ÚNICO que no lleva ningún adaptador.

    Medido en la cámara `mesa`, misma semilla, «sostiene el móvil con las dos
    manos y mira la pantalla»:

        QUIÉN, ROPA, acción, ambiente     no hay móvil por ninguna parte
        (acción:1.2), quién, ambiente     aparece el móvil; se pierde el mono
        (acción:1.2), ambiente            sala preciosa, persona genérica
        (acción:1.2), quién, amb., ropa   móvil, mono y cara                <--

    La ropa al final y no al principio: ahí ya no compite con la acción, y con
    el adaptador de vestuario sujetándola por la imagen, con nombrarla basta.
    """
    quienes = [B.ELENCO[c] for c in esc.personajes if c in B.ELENCO]
    gente = ", ".join(p.breve for p in quienes)
    ropa = ", ".join(p.vestuario for p in quienes if p.vestuario)
    trozos = [f"({esc.accion}:1.2)" if esc.accion else ""]
    if gente:
        trozos.append(f"({gente}:1.1)")
    trozos.append(B.ESTILO)
    if ropa:
        trozos.append(f"({ropa}:1.1)")
    return ", ".join(x for x in trozos if x)


def negativo_de(esc: "Gu.Escena") -> str:
    """El negativo del plano: el de estilo, más el sexo que no toca, más `evitar`.

    El sexo va aquí y no en el positivo por una razón medida: el positivo ya
    dice quién es —«a man with a full dark beard»— y aun así el mismo personaje,
    en la misma cámara y con la misma ficha, salió hombre en un plano y **mujer**
    en el siguiente. La palabra estaba puesta; lo que fallaba es que competía con
    todo lo demás. En el negativo no compite con nada: no hay más que una cosa
    que no puede aparecer, y no aparece.

    Solo se escribe cuando hay UNA persona anclada. Con dos, pedir que no haya
    mujeres en un plano donde hay una mujer sería justo lo contrario de lo que se
    quiere, y el estudio ya prohíbe en `video_servicio.py` anclar más de una.
    """
    partes = [B.ESTILO_NEGATIVO]
    quienes = [B.ELENCO[c] for c in esc.personajes if c in B.ELENCO]
    if len(quienes) == 1 and quienes[0].sexo in ("h", "m"):
        partes.append("woman, female" if quienes[0].sexo == "h" else "man, male")
    if esc.evitar:
        partes.append(esc.evitar)
    return ", ".join(partes)


def _controles_al_dia(bib: B.Biblia) -> None:
    """Los mapas de las cámaras se generan si faltan. Son deterministas: no caducan."""
    falta = [c for c in B.CAMARAS if not (B.DIR_CONTROL / f"{c}_profundidad.png").exists()]
    if falta:
        G.generar_controles(bib)


def producir(prompt: str, t: Trabajo, usar_llm: bool = True, con_voz: bool = True,
             solo_guion: bool = False, guion_hecho: "Gu.Guion | None" = None,
             elegidos: list[str] | None = None, publicar: bool = True) -> dict:
    """Todo el proceso. Devuelve el estado final.

    `guion_hecho` salta al guionista y rueda un guion escrito a mano. Es lo que
    usan las pruebas de moldes, donde lo que se quiere no es que un modelo decida
    las escenas, sino repetir exactamente las mismas para todo el elenco.

    `publicar=False` deja el vídeo en `salidas/` y no lo sube. Es para el primer
    pase de un guion nuevo: que estén los doce planos —lo único que sabe mirar el
    guarda de más abajo— no quiere decir que sean BUENOS, y eso solo se ve
    mirándolos. Pasó con este mismo estudio: tres planos completos, «exit 0,
    publicado», y en cuadro una cocina doméstica con sillas verdes en vez de la
    cantina y una azafata de vuelo haciendo de camarero.
    """
    t.estado["prompt"] = prompt
    t.estado["fase"] = "guion"
    t.anotar("escribiendo el guion", 0.02)

    bib = B.cargar()
    g = guion_hecho or Gu.escribir(prompt, bib, usar_llm=usar_llm, elegidos=elegidos)
    t.estado["titulo"] = g.titulo
    t.estado["avisos"].extend(g.avisos)
    t.estado["escenas"] = [asdict(e) for e in g.escenas]
    (t.dir / "guion.json").write_text(
        json.dumps(g.a_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
    t.anotar(f"guion de {len(g.escenas)} planos ({g.segundos} s)", 0.06)

    if solo_guion:
        t.estado["fase"] = "guion listo"
        t.guardar()
        return t.estado

    _controles_al_dia(bib)
    marca = bib.local.get("local_nombre") or "Cantina Vesta-9"

    # ── 1. Lo que no gasta GPU: pantallas y voz ─────────────────────────
    t.estado["fase"] = "pantallas"
    crudos: list[dict] = []
    for i, esc in enumerate(g.escenas):
        parte = 0.06 + 0.24 * (i / max(1, len(g.escenas)))
        info: dict = {"i": i, "camara": esc.camara, "segundos": esc.segundos}
        if esc.pantalla:
            t.anotar(f"grabando {B.PANTALLAS[esc.pantalla][2]}", parte)
            try:
                # Cada plano graba en SU carpeta. `grabar` nombra el fichero por
                # la clave de pantalla, así que dos planos de la misma pantalla
                # —el TPV al abrir la mesa y el TPV al emitir la factura— se
                # pisaban: el segundo borraba al primero y los dos acababan
                # enseñando la misma toma.
                w = P.grabar(esc.pantalla, segundos=esc.segundos,
                             con_tutorial=esc.tutorial, gesto=esc.gesto or None,
                             destino=t.dir / "crudos" / f"{i:02d}", avisar=t.avisar)
                info["clip"] = str(w)
                info["origen"] = "pantalla"
            except Exception as e:
                t.avisar(f"Plano {i+1}: no se pudo grabar «{esc.pantalla}» ({e}).")
                info["origen"] = "fallo"
        crudos.append(info)

    t.estado["fase"] = "voz"
    voces: dict[int, Path] = {}
    if con_voz and any(e.narracion for e in g.escenas):
        if V.disponible():
            for i, esc in enumerate(g.escenas):
                if not esc.narracion:
                    continue
                t.anotar(f"poniendo voz al plano {i+1}", 0.30 + 0.10 * (i / max(1, len(g.escenas))))
                try:
                    voces[i] = V.hablar(esc.narracion, t.dir / "voz" / f"{i:02d}.wav",
                                        trabajo=t.id)
                except Exception as e:
                    t.avisar(f"Plano {i+1}: sin voz ({e}).")
        else:
            t.avisar("Raspa no responde para Piper: el vídeo saldrá con subtítulos y sin voz.")

    # ── 2. Lo que sí gasta GPU ──────────────────────────────────────────
    # Si la GPU no está, se entrega lo que haya (las pantallas grabadas) y se dice
    # qué falta. Tirar a la basura un tutorial entero porque otro proceso tenía la
    # tarjeta —y en esta máquina la tienen a menudo: los relatos, los cursos, el
    # pipeline de Star Citizen— sería perder el trabajo que sí se pudo hacer.
    t.estado["fase"] = "imagen"
    hay_gpu = True
    motivo_sin_gpu = ""
    if any(c.get("origen") != "pantalla" for c in crudos):
        if not C.encendido():
            hay_gpu, motivo_sin_gpu = False, "ComfyUI no está arrancado (Kinemato\\run.bat)"
        else:
            libre, total = C.vram_libre()
            if libre < VRAM_MINIMA:
                hay_gpu = False
                motivo_sin_gpu = (f"solo hay {libre} MiB de {total} libres en la GPU y hacen "
                                  f"falta ~{VRAM_MINIMA}; {C.quien_ocupa_la_gpu()}")
        if not hay_gpu:
            t.avisar(f"Sin generación de imagen: {motivo_sin_gpu}. Se monta con las pantallas "
                     "grabadas; cuando se libere la tarjeta, vuelve a lanzar el mismo prompt.")

    for i, esc in enumerate(g.escenas):
        info = crudos[i]
        if info.get("origen") == "pantalla":
            continue
        if not hay_gpu:
            continue
        parte = 0.40 + 0.40 * (i / max(1, len(g.escenas)))
        t.anotar(f"generando el plano {i+1} de {len(g.escenas)} ({esc.camara})", parte)

        control = B.DIR_CONTROL / f"{esc.camara}_profundidad.png"
        vacia = G.camara_vacia(esc.camara)
        if vacia is not None:
            t.avisar(f"Plano {i+1}: la cámara «{esc.camara}» apenas ve geometría "
                     f"({vacia:.0%} del encuadre). Sin nada que sujetar, la persona saldrá "
                     "posando en un sitio que no es la cantina. Se arregla dibujando esa "
                     "parte en plano.html, no bajando ni subiendo la fuerza de ControlNet.")
        referencia = E.referencia_para(esc.personajes)
        if esc.personajes and not referencia:
            t.avisar(f"Plano {i+1}: sin retrato de {esc.personajes[0]}; la persona saldrá "
                     "genérica. Haz el casting para que sea siempre la misma.")
        elif esc.personajes and len(referencia) == 1:
            t.avisar(f"Plano {i+1}: {esc.personajes[0]} solo tiene el retrato frontal. "
                     "Con la hoja de personaje entera aguanta mucho mejor cuando gira la cabeza "
                     "(`python estudio_cli.py hojas`).")

        positivo = prompt_de(esc)
        fotogramas = max(16, esc.segundos * B.FORMATO["fps"])

        semilla = esc.semilla(B.FORMATO["semilla_base"], i)
        if B.FORMATO.get("modo", "fijo") == "fijo":
            # Plano fijo + movimiento de cámara: 36 s de GPU en vez de 17 min, y
            # con mejor imagen. El movimiento lo pone el montaje.
            cuerpo = E.cuerpo_de(esc.personajes[0]) if esc.personajes else None
            grafo = C.construir_fijo(
                prompt_positivo=positivo, prompt_negativo=negativo_de(esc),
                control=control, semilla=semilla,
                prefijo=f"kds_{t.id}_{i:02d}", referencia=referencia, cuerpo=cuerpo)
            pid = C.encolar(grafo)
            salidas = C.esperar(pid, aviso=lambda s, e, i=i: t.anotar(
                f"plano {i+1}: {e}, {s} s", None))
            imagenes = [s for s in salidas if s.suffix.lower() in (".png", ".jpg")]
            if not imagenes:
                t.avisar(f"Plano {i+1}: la generación no dejó imagen; se salta.")
                continue
            info["imagen"] = str(imagenes[0])
            info["origen"] = "fijo"
        else:
            grafo = C.construir(
                prompt_positivo=positivo, prompt_negativo=negativo_de(esc),
                control=control, fotogramas=fotogramas, semilla=semilla,
                prefijo=f"kds_{t.id}_{i:02d}", referencia=referencia)
            pid = C.encolar(grafo)
            salidas = C.esperar(pid, aviso=lambda s, e, i=i: t.anotar(
                f"plano {i+1}: {e}, {s} s", None))
            clips = [s for s in salidas if s.suffix.lower() == ".mp4"]
            if not clips:
                t.avisar(f"Plano {i+1}: la generación no dejó vídeo; se salta.")
                continue
            info["clip"] = str(clips[0])
            info["origen"] = "generado"

    # ── 3. Montaje ──────────────────────────────────────────────────────
    t.estado["fase"] = "montaje"
    t.anotar("normalizando los planos", 0.82)

    normalizados: list[Path] = []
    audios: list[Path] = []
    tramos: list[tuple[float, float, str]] = []
    reloj = 0.0

    for i, esc in enumerate(g.escenas):
        info = crudos[i]
        if not (info.get("clip") or info.get("imagen")):
            continue
        # Manda la voz: si la frase dura más que el plano, el plano se estira.
        segundos = float(esc.segundos)
        if i in voces:
            segundos = max(segundos, V.duracion(voces[i]) + 0.6)

        destino = t.dir / "planos" / f"{i:02d}.mp4"
        try:
            if info.get("imagen"):
                mov = M.movimiento_de(i, esc.camara)
                info["movimiento"] = mov
                normalizados.append(M.desde_imagen(
                    Path(info["imagen"]), destino, segundos, movimiento=mov,
                    rotulo=esc.rotulo, marca=marca))
            else:
                clip = Path(info["clip"])
                normalizados.append(M.normalizar(clip, destino, segundos,
                                                 rotulo=esc.rotulo, marca=marca,
                                                 desde=P.desde_de(clip)))
        except Exception as e:
            t.avisar(f"Plano {i+1}: no se pudo montar ({e}); se salta.")
            continue
        audios.append(M.pista_de_voz(voces.get(i), segundos, t.dir / "audio" / f"{i:02d}.wav"))
        if esc.narracion:
            tramos.append((reloj, reloj + segundos, esc.narracion))
        reloj += segundos

    if not normalizados:
        if not hay_gpu:
            raise RuntimeError(
                f"todos los planos de este guion eran generados y no hay GPU: {motivo_sin_gpu}. "
                "Un guion con alguna pantalla del KDS sí se habría podido montar.")
        raise RuntimeError("no quedó ningún plano utilizable")

    srt = None
    if tramos:
        srt = V.subtitulos(tramos, t.dir / "subtitulos.srt")

    t.anotar("montando el vídeo", 0.92)
    DIR_SALIDAS.mkdir(parents=True, exist_ok=True)
    nombre = f"{t.id}_{_limpiar(g.titulo)}.mp4"
    final = DIR_SALIDAS / nombre
    M.unir(normalizados, audios, final, srt)

    portada = DIR_SALIDAS / (final.stem + ".jpg")
    try:
        M.portada(final, portada)
        t.estado["portada"] = portada.name
    except Exception:
        pass
    if srt:
        destino_srt = DIR_SALIDAS / (final.stem + ".srt")
        shutil.copy2(srt, destino_srt)
        t.estado["srt"] = destino_srt.name

    t.estado["salida"] = final.name
    t.estado["segundos"] = round(reloj, 1)

    # Publicar en Raspa es parte de terminar: un vídeo que solo existe en Pecera
    # no lo ve nadie más. Si falla, el trabajo NO se da por roto: el MP4 está
    # hecho y se puede subir después.
    #
    # Pero un vídeo al que le FALTAN planos no se publica. Se monta y se entrega
    # —el trabajo hecho no se tira, y por eso la GPU caída no aborta nada— y se
    # queda en `salidas/` para mirarlo. La página de Raspa es el escaparate del
    # sistema: un ejemplo visual con cinco planos de doce puesto ahí se lee como
    # el producto terminado. Ya pasó, y de la peor manera: con ComfyUI apagado el
    # proceso acabó en «exit 0, publicado» y sin una sola persona en cuadro.
    faltan = [c["i"] + 1 for c in crudos if c.get("origen") in (None, "fallo")]
    if faltan:
        t.avisar(f"NO publicado: faltan los planos {faltan} de {len(crudos)}. "
                 f"El vídeo está en salidas/{final.name}; arregla lo que dicen los "
                 "avisos de arriba y vuelve a lanzar el mismo prompt.")
    elif not publicar:
        t.anotar(f"sin publicar por petición: salidas/{final.name}", 0.97)
    else:
        t.anotar("publicando en Raspa", 0.97)
        try:
            t.estado["url"] = Pub.publicar(DIR_SALIDAS, solo=[final.name])
        except Exception as e:
            t.avisar(f"No se pudo publicar en home.pr1.es/videos ({e}). El vídeo está en salidas/.")

    t.estado["fase"] = "listo"
    t.anotar("listo", 1.0)
    return t.estado


# ── Cola: un trabajo cada vez, porque la GPU es una ─────────────────────
_candado = threading.Lock()
_en_marcha: dict[str, threading.Thread] = {}


def lanzar(prompt: str, usar_llm: bool = True, con_voz: bool = True,
           solo_guion: bool = False, elegidos: list[str] | None = None) -> str:
    ident = _nuevo_id()
    while (DIR_TRABAJOS / ident).exists():
        time.sleep(1)
        ident = _nuevo_id()
    t = Trabajo(ident)
    t.estado["prompt"] = prompt
    t.guardar()

    def correr() -> None:
        with _candado:          # la GPU es una: los trabajos hacen cola
            try:
                producir(prompt, t, usar_llm=usar_llm, con_voz=con_voz,
                         solo_guion=solo_guion, elegidos=elegidos)
            except Exception as e:
                t.estado["fase"] = "error"
                t.estado["error"] = str(e)
                (t.dir / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
                t.guardar()

    hilo = threading.Thread(target=correr, name=f"produccion-{ident}", daemon=True)
    _en_marcha[ident] = hilo
    hilo.start()
    return ident


def _limpiar(texto: str) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower()
    return (t or "video")[:48]
