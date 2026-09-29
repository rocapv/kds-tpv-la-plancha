"""Publicar los vídeos en Raspa: `https://home.pr1.es/videos`, solo desde la LAN.

Los vídeos se ven donde se ve el KDS, que es donde la gente ya mira. Pero
`home.pr1.es` está **abierto a internet** por decisión expresa —por ahí se teclea
el PIN desde fuera—, así que el directorio lleva su propia guarda en Apache
(`Require ip 192.168.1.0/24`). Sin ella, subir el primer vídeo sería publicarlo
al mundo.

Dos detalles de dónde vive:

· Fuera de `/var/www/html`, porque ese directorio lo reescribe el despliegue del
  KDS cada vez que publica el frontend y se llevaría los vídeos por delante.
· El índice se genera aquí y se sube como un fichero más: Apache tiene los
  listados apagados (`Options -Indexes`), y así la página se puede cuidar en vez
  de depender del listado automático del servidor.
"""
from __future__ import annotations

import html
import subprocess
from datetime import datetime
from pathlib import Path

RASPA = "roca@192.168.1.100"
CLAVE = "C:/Users/Roca/.ssh/roca"
PUERTO = "2222"
DESTINO = "/var/www/videos"
URL = "https://home.pr1.es/videos/"

_SSH = ["ssh", "-i", CLAVE, "-p", PUERTO, "-o", "ConnectTimeout=20",
        "-o", "StrictHostKeyChecking=accept-new", RASPA]
_SCP = ["scp", "-i", CLAVE, "-P", PUERTO, "-o", "ConnectTimeout=20",
        "-o", "StrictHostKeyChecking=accept-new"]


class NoSePudo(RuntimeError):
    pass


def disponible() -> bool:
    try:
        r = subprocess.run(_SSH + [f"test -d {DESTINO} && echo si"],
                           capture_output=True, text=True, timeout=30)
        return "si" in r.stdout
    except Exception:
        return False


def _subir(fichero: Path) -> None:
    r = subprocess.run(_SCP + [str(fichero), f"{RASPA}:{DESTINO}/{fichero.name}"],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise NoSePudo(f"no se pudo subir {fichero.name}: {(r.stderr or '')[-200:]}")


def _listar() -> list[str]:
    r = subprocess.run(_SSH + [f"ls -1 {DESTINO}"], capture_output=True, text=True, timeout=60)
    return [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]


def _indice(videos: list[dict]) -> str:
    filas = []
    for v in videos:
        portada = (f'<img src="{html.escape(v["portada"])}" alt="">'
                   if v.get("portada") else '<div class="sin"></div>')
        subs = (f' · <a href="{html.escape(v["srt"])}" download>subtítulos</a>'
                if v.get("srt") else "")
        filas.append(f"""    <figure>
      <video controls preload="none" poster="{html.escape(v.get('portada') or '')}"
             src="{html.escape(v['mp4'])}"></video>
      <figcaption><b>{html.escape(v['titulo'])}</b><br>
        <span>{html.escape(v['fecha'])}</span>
        · <a href="{html.escape(v['mp4'])}" download>descargar</a>{subs}</figcaption>
    </figure>""")
        del portada

    cuerpo = "\n".join(filas) or '    <p class="nada">Todavía no hay vídeos publicados.</p>'
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vídeos · Cantina Vesta-9</title>
<style>
  body {{ margin:0; background:#100d0c; color:#e9e4de;
         font:15px/1.5 "Segoe UI",system-ui,sans-serif; }}
  header {{ padding:22px 28px; border-bottom:1px solid #2c2724; }}
  h1 {{ font-size:19px; margin:0; font-weight:600; }}
  header p {{ color:#9a908a; font-size:13px; margin:6px 0 0; }}
  main {{ max-width:1180px; margin:0 auto; padding:24px 28px 80px;
          display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:18px; }}
  figure {{ margin:0; }}
  video, .sin {{ width:100%; border-radius:8px; background:#000; display:block; aspect-ratio:16/9; }}
  figcaption {{ color:#9a908a; font-size:13px; margin-top:7px; }}
  figcaption b {{ color:#e9e4de; font-weight:600; }}
  a {{ color:#d68910; }}
  .nada {{ color:#9a908a; }}
</style>
</head>
<body>
<header>
  <h1>Vídeos · Cantina Vesta-9</h1>
  <p>Tutoriales del KDS+TPV y escenas de sala. Solo desde la red local.</p>
</header>
<main>
{cuerpo}
</main>
</body>
</html>
"""


def publicar(salidas: Path, solo: list[str] | None = None) -> str:
    """Sube lo que haya en `salidas/` y regenera el índice. Devuelve la URL."""
    if not disponible():
        raise NoSePudo(f"Raspa no responde o no existe {DESTINO}")

    mp4s = sorted(salidas.glob("*.mp4"), key=lambda f: f.name, reverse=True)
    if solo:
        mp4s = [m for m in mp4s if m.name in solo]
    if not mp4s:
        raise NoSePudo("no hay vídeos que publicar")

    ya = set(_listar())
    for mp4 in mp4s:
        for f in (mp4, mp4.with_suffix(".jpg"), mp4.with_suffix(".srt")):
            if f.exists() and f.name not in ya:
                _subir(f)

    # El índice se rehace con TODO lo que hay allí, no solo con lo recién subido:
    # así no desaparecen de la página los vídeos de días anteriores.
    allí = set(_listar())
    videos = []
    for nombre in sorted((n for n in allí if n.endswith(".mp4")), reverse=True):
        tallo = nombre[:-4]
        titulo = tallo
        fecha = ""
        if len(tallo) > 16 and tallo[8] == "_":
            try:
                fecha = datetime.strptime(tallo[:15], "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M")
                titulo = tallo[16:].replace("_", " ").strip().capitalize() or tallo
            except ValueError:
                pass
        videos.append({
            "mp4": nombre, "titulo": titulo, "fecha": fecha,
            "portada": f"{tallo}.jpg" if f"{tallo}.jpg" in allí else "",
            "srt": f"{tallo}.srt" if f"{tallo}.srt" in allí else "",
        })

    local = salidas / "_index.html"
    local.write_text(_indice(videos), encoding="utf-8")
    r = subprocess.run(_SCP + [str(local), f"{RASPA}:{DESTINO}/index.html"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise NoSePudo(f"no se pudo subir el índice: {(r.stderr or '')[-200:]}")
    local.unlink(missing_ok=True)
    return URL
