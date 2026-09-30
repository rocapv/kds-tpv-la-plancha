"""El montaje: clips sueltos, voz y subtítulos → un MP4 que se puede enseñar.

Todo pasa por aquí para que salga siempre igual: 1920×1080, 24 fotogramas por
segundo, el mismo fundido entre planos, los mismos rótulos y la misma mosca con
el nombre del local. Los clips llegan de dos sitios muy distintos —los generados
por AnimateDiff, a 640×360 y 8 fps, y las pantallas grabadas del KDS, que pueden
ser una tableta apaisada o un móvil de pie— y salen del mismo molde.

El vertical no se resuelve con dos barras negras: el fondo es el propio plano
ampliado y desenfocado. Es un truco viejo de televisión y es lo que hace que un
móvil grabado quepa en un vídeo apaisado sin que parezca un error.

La duración de cada plano la manda la NARRACIÓN, no el guion: si la frase dura
más que el clip, se congela el último fotograma hasta que termina de hablar.
Cortar a alguien a media palabra se nota siempre.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import biblia as B

_CANDIDATOS = [
    Path("M:/CLAUDE/.tools/bin/ffmpeg.exe"),
    Path(__file__).resolve().parents[3] / ".tools" / "bin" / "ffmpeg.exe",
]

FUENTE = "C\\:/Windows/Fonts/segoeuib.ttf"      # escapada para el filtro de ffmpeg
FUNDIDO = 0.35                                   # segundos de entrada y salida por plano


class SinFfmpeg(RuntimeError):
    pass


def ffmpeg() -> str:
    hallado = shutil.which("ffmpeg")
    if hallado:
        return hallado
    for c in _CANDIDATOS:
        if c.exists():
            return str(c)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise SinFfmpeg("no hay ffmpeg: ni en PATH, ni en .tools/bin, ni en imageio_ffmpeg")


def _correr(args: list[str], que: str) -> None:
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        cola = (r.stderr or "")[-1500:]
        raise RuntimeError(f"ffmpeg falló al {que}:\n{cola}")


def duracion(fichero: Path) -> float:
    """Segundos de un fichero, preguntándoselo a ffmpeg (sin ffprobe aparte)."""
    r = subprocess.run([ffmpeg(), "-i", str(fichero)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for linea in (r.stderr or "").splitlines():
        if "Duration:" in linea:
            crudo = linea.split("Duration:")[1].split(",")[0].strip()
            try:
                h, m, s = crudo.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
            except ValueError:
                return 0.0
    return 0.0


def _escapar(texto: str) -> str:
    """drawtext se come las comas, los dos puntos y las comillas si no se escapan."""
    return (texto.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")
            .replace("%", "\\%").replace(",", "\\,"))


def _linea_concat(fichero: Path) -> str:
    """Una l\u00ednea del fichero de lista de `concat`, con la comilla escapada.

    El demuxer delimita cada ruta con comillas simples, as\u00ed que una comilla
    DENTRO de la ruta la cierra por la mitad. Y la ruta de este repositorio
    tiene una: \u00ab...1 d'Administraci\u00f3 de Sistemes...\u00bb. El resultado era que
    ffmpeg intentaba abrir \u00abM:/CLAUDE/ASIR/212438_Projecte intermodular 1 d\u00bb y
    se quejaba de un fichero que nadie hab\u00eda nombrado. Dentro de comillas
    simples no se puede escapar: hay que cerrar, poner la comilla suelta y
    volver a abrir.
    """
    return "file '" + fichero.as_posix().replace("'", "'\\''") + "'\n"


def normalizar(clip: Path, destino: Path, segundos: float, rotulo: str = "",
               marca: str = "", desde: float = 0.0) -> Path:
    """Un plano cualquiera → 1920×1080 a 24 fps, con su duración exacta.

    `desde` salta los primeros segundos del clip. Lo usan las pantallas en las
    que hay que HACER algo antes de que se vea lo que el plano promete —abrir la
    mesa y pulsar «Cobrar», por ejemplo—: esos clics ocupan el principio del
    vídeo y lo que interesa queda al final. Sin este salto, el plano del cobro
    enseñaba el mapa de mesas, que es justo lo que enseña el plano anterior.
    """
    f = B.FORMATO
    ancho, alto, fps = f["ancho_final"], f["alto_final"], f["fps_final"]

    fundido_salida = max(0.0, segundos - FUNDIDO)
    filtros = [
        # Fondo: el propio plano, ampliado, recortado y desenfocado.
        f"[0:v]scale={ancho}:{alto}:force_original_aspect_ratio=increase,"
        f"crop={ancho}:{alto},boxblur=28:2,eq=brightness=-0.12[fondo]",
        # Frente: el plano entero, sin recortar, centrado sobre el fondo.
        f"[0:v]scale={ancho}:{alto}:force_original_aspect_ratio=decrease:flags=lanczos[frente]",
        "[fondo][frente]overlay=(W-w)/2:(H-h)/2[compuesto]",
        # tpad congela el último fotograma si el plano se queda corto para la voz.
        f"[compuesto]fps={fps},tpad=stop_mode=clone:stop_duration=30,"
        f"trim=duration={segundos:.3f},setpts=PTS-STARTPTS,"
        f"fade=t=in:st=0:d={FUNDIDO},fade=t=out:st={fundido_salida:.3f}:d={FUNDIDO}[base]",
    ]

    ultimo = "base"
    if rotulo:
        filtros.append(
            f"[{ultimo}]drawtext=fontfile='{FUENTE}':text='{_escapar(rotulo)}':"
            f"fontcolor=white:fontsize=46:box=1:boxcolor=0x0c0c0eCC:boxborderw=22:"
            f"x=80:y=h-190:alpha='if(lt(t,0.4),t/0.4,if(lt(t,{max(0.6, segundos-0.6):.2f}),1,"
            f"max(0,({segundos:.2f}-t)/0.6)))'[rot]")
        ultimo = "rot"
    if marca:
        filtros.append(
            f"[{ultimo}]drawtext=fontfile='{FUENTE}':text='{_escapar(marca)}':"
            f"fontcolor=0xE8E8EAAA:fontsize=26:x=w-tw-46:y=46[mar]")
        ultimo = "mar"

    destino.parent.mkdir(parents=True, exist_ok=True)
    # El `-ss` va ANTES del `-i`: así ffmpeg busca en el fichero en vez de
    # decodificarlo entero y tirar lo que sobra.
    salto = ["-ss", f"{desde:.3f}"] if desde > 0 else []
    _correr([ffmpeg(), "-y", *salto, "-i", str(clip),
             "-filter_complex", ";".join(filtros), "-map", f"[{ultimo}]",
             "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-r", str(fps), str(destino)],
            f"normalizar {clip.name}")
    return destino


# ── Movimiento de cámara sobre un plano fijo ────────────────────────────────
# Los planos se generan como IMAGEN y el movimiento lo pone la cámara, no el
# modelo. Es la técnica de toda la vida del documental, y aquí además es la
# decisión técnica correcta: una imagen sola cuesta 36 segundos de GPU y sale
# nítida, mientras que animarla con AnimateDiff cuesta 17 minutos y sale peor,
# porque reparte el mismo modelo entre veinticuatro fotogramas.
#
# La imagen llega a 3072x1728, muy por encima de los 1920x1080 de salida: ese
# sobrante es lo que se gasta al acercarse, y por eso el zoom no pixela.
MOVIMIENTOS = ["acercar", "alejar", "derecha", "izquierda", "acercar_derecha"]
ZOOM = 1.18            # cuánto llega a acercarse


def _expresion_camara(movimiento: str, total: int) -> tuple[str, str, str]:
    """(zoom, x, y) como expresiones de zoompan. `on` es el fotograma actual."""
    avance = f"(on/{max(1, total - 1)})"
    z_in = f"1+{ZOOM - 1:.3f}*{avance}"
    z_out = f"{ZOOM:.3f}-{ZOOM - 1:.3f}*{avance}"
    centro_x, centro_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"

    if movimiento == "acercar":
        return z_in, centro_x, centro_y
    if movimiento == "alejar":
        return z_out, centro_x, centro_y
    if movimiento == "derecha":
        return f"{ZOOM:.3f}", f"(iw-iw/zoom)*{avance}", centro_y
    if movimiento == "izquierda":
        return f"{ZOOM:.3f}", f"(iw-iw/zoom)*(1-{avance})", centro_y
    # acercar_derecha: las dos cosas a la vez, que es lo que más parece una cámara
    return z_in, f"(iw-iw/zoom)*{avance}", centro_y


def movimiento_de(indice: int, camara: str) -> str:
    """Siempre el mismo movimiento para el mismo plano: nada al azar."""
    return MOVIMIENTOS[(indice + sum(map(ord, camara))) % len(MOVIMIENTOS)]


def desde_imagen(imagen: Path, destino: Path, segundos: float, movimiento: str = "acercar",
                 rotulo: str = "", marca: str = "") -> Path:
    """Una imagen fija + movimiento de cámara = un plano de vídeo."""
    f = B.FORMATO
    ancho, alto, fps = f["ancho_final"], f["alto_final"], f["fps_final"]
    total = max(2, int(round(segundos * fps)))
    z, x, y = _expresion_camara(movimiento, total)
    fundido_salida = max(0.0, segundos - FUNDIDO)

    filtros = [
        # zoompan trabaja mejor sobre una imagen mayor que la salida; la de
        # entrada ya viene a 3072x1728, así que solo se encaja la proporción.
        f"[0:v]scale={ancho * 2}:{alto * 2}:force_original_aspect_ratio=increase,"
        f"crop={ancho * 2}:{alto * 2},setsar=1[grande]",
        f"[grande]zoompan=z='{z}':x='{x}':y='{y}':d={total}:s={ancho}x{alto}:fps={fps}[mov]",
        f"[mov]fade=t=in:st=0:d={FUNDIDO},fade=t=out:st={fundido_salida:.3f}:d={FUNDIDO}[base]",
    ]

    ultimo = "base"
    if rotulo:
        filtros.append(
            f"[{ultimo}]drawtext=fontfile='{FUENTE}':text='{_escapar(rotulo)}':"
            f"fontcolor=white:fontsize=46:box=1:boxcolor=0x0c0c0eCC:boxborderw=22:"
            f"x=80:y=h-190[rot]")
        ultimo = "rot"
    if marca:
        filtros.append(
            f"[{ultimo}]drawtext=fontfile='{FUENTE}':text='{_escapar(marca)}':"
            f"fontcolor=0xE8E8EAAA:fontsize=26:x=w-tw-46:y=46[mar]")
        ultimo = "mar"

    destino.parent.mkdir(parents=True, exist_ok=True)
    # La imagen entra UNA vez, sin `-loop`. zoompan genera `d` fotogramas por cada
    # fotograma que recibe: con la imagen repetida 96 veces por el loop, salían
    # 96x96 = 9.216 fotogramas y cada plano duraba 6 minutos y 40 segundos en vez
    # de cuatro. El `-t` de salida es el cinturón por si acaso.
    _correr([ffmpeg(), "-y", "-i", str(imagen),
             "-filter_complex", ";".join(filtros), "-map", f"[{ultimo}]",
             "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-r", str(fps), "-t", f"{segundos:.3f}",
             str(destino)],
            f"animar {imagen.name}")
    return destino


def pista_de_voz(wav: Path | None, segundos: float, destino: Path) -> Path:
    """Un WAV de la duración exacta del plano: la voz al principio, silencio detrás."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if wav and wav.exists():
        _correr([ffmpeg(), "-y", "-i", str(wav),
                 "-af", f"apad,atrim=duration={segundos:.3f},aresample=48000",
                 "-ac", "2", "-c:a", "pcm_s16le", str(destino)], "ajustar la voz")
    else:
        _correr([ffmpeg(), "-y", "-f", "lavfi", "-i",
                 f"anullsrc=channel_layout=stereo:sample_rate=48000",
                 "-t", f"{segundos:.3f}", "-c:a", "pcm_s16le", str(destino)], "hacer silencio")
    return destino


def unir(videos: list[Path], audios: list[Path], destino: Path,
         srt: Path | None = None) -> Path:
    """Concatena los planos ya normalizados y les pega la voz y los subtítulos."""
    if not videos:
        raise RuntimeError("no hay nada que montar")
    tmp = destino.parent / "_lista"
    tmp.mkdir(parents=True, exist_ok=True)

    lista_v = tmp / "videos.txt"
    lista_v.write_text("".join(_linea_concat(v) for v in videos), encoding="utf-8")
    mudo = tmp / "mudo.mp4"
    _correr([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(lista_v),
             "-c", "copy", str(mudo)], "juntar los planos")

    pista = None
    if audios:
        lista_a = tmp / "audios.txt"
        lista_a.write_text("".join(_linea_concat(a) for a in audios), encoding="utf-8")
        pista = tmp / "voz.wav"
        _correr([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(lista_a),
                 "-c", "copy", str(pista)], "juntar la voz")

    args = [ffmpeg(), "-y", "-i", str(mudo)]
    if pista:
        args += ["-i", str(pista)]
    if srt and srt.exists():
        args += ["-i", str(srt)]

    args += ["-map", "0:v"]
    if pista:
        args += ["-map", "1:a"]
    if srt and srt.exists():
        args += ["-map", f"{2 if pista else 1}:s", "-c:s", "mov_text",
                 "-metadata:s:s:0", "language=spa"]
    args += ["-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(destino)]

    destino.parent.mkdir(parents=True, exist_ok=True)
    _correr(args, "pegar voz y subtítulos")
    shutil.rmtree(tmp, ignore_errors=True)
    return destino


def portada(video: Path, destino: Path, segundo: float = 1.0) -> Path:
    """Un fotograma para la galería."""
    _correr([ffmpeg(), "-y", "-ss", f"{segundo}", "-i", str(video),
             "-frames:v", "1", "-q:v", "3", str(destino)], "sacar la portada")
    return destino
