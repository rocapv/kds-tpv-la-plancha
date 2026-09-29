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


def _controles_al_dia(bib: B.Biblia) -> None:
    """Los mapas de las cámaras se generan si faltan. Son deterministas: no caducan."""
    falta = [c for c in B.CAMARAS if not (B.DIR_CONTROL / f"{c}_profundidad.png").exists()]
    if falta:
        G.generar_controles(bib)


def producir(prompt: str, t: Trabajo, usar_llm: bool = True, con_voz: bool = True,
             solo_guion: bool = False, guion_hecho: "Gu.Guion | None" = None,
             elegidos: list[str] | None = None) -> dict:
    """Todo el proceso. Devuelve el estado final.

    `guion_hecho` salta al guionista y rueda un guion escrito a mano. Es lo que
    usan las pruebas de moldes, donde lo que se quiere no es que un modelo decida
    las escenas, sino repetir exactamente las mismas para todo el elenco.
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
                w = P.grabar(esc.pantalla, segundos=esc.segundos,
                             destino=t.dir / "crudos")
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
        referencia = E.referencia_para(esc.personajes)
        if esc.personajes and not referencia:
            t.avisar(f"Plano {i+1}: sin retrato de {esc.personajes[0]}; la persona saldrá "
                     "genérica. Haz el casting para que sea siempre la misma.")
        elif esc.personajes and len(referencia) == 1:
            t.avisar(f"Plano {i+1}: {esc.personajes[0]} solo tiene el retrato frontal. "
                     "Con la hoja de personaje entera aguanta mucho mejor cuando gira la cabeza "
                     "(`python estudio_cli.py hojas`).")

        # El orden importa y no es el natural: primero QUIÉN y QUÉ hace, con
        # peso explícito, y el ambiente al final. Al revés, el decorado se come
        # el prompt y la gente no llega a aparecer.
        gente = ", ".join(B.ELENCO[c].breve for c in esc.personajes if c in B.ELENCO)
        if esc.personajes:
            cabeza = f"({gente}:1.3), {esc.accion}" if gente else esc.accion
        else:
            cabeza = esc.accion
        positivo = ", ".join(x for x in [cabeza, B.ESTILO] if x)
        fotogramas = max(16, esc.segundos * B.FORMATO["fps"])

        grafo = C.construir(
            prompt_positivo=positivo, prompt_negativo=B.ESTILO_NEGATIVO,
            control=control, fotogramas=fotogramas,
            semilla=esc.semilla(B.FORMATO["semilla_base"], i),
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
        if not info.get("clip"):
            continue
        clip = Path(info["clip"])
        # Manda la voz: si la frase dura más que el plano, el plano se estira.
        segundos = float(esc.segundos)
        if i in voces:
            segundos = max(segundos, V.duracion(voces[i]) + 0.6)

        destino = t.dir / "planos" / f"{i:02d}.mp4"
        try:
            normalizados.append(M.normalizar(clip, destino, segundos,
                                             rotulo=esc.rotulo, marca=marca))
        except Exception as e:
            t.avisar(f"Plano {i+1}: no se pudo normalizar ({e}); se salta.")
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
