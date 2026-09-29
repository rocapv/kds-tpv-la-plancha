"""La narración: Piper en Raspa, y los subtítulos salen del mismo texto.

Piper está instalado en Raspa (`~/piper`) con dos voces castellanas. Se hace
allí y no aquí por lo de siempre: lo que puede hacer Raspa, lo hace Raspa, y así
la GPU de Pecera queda para lo que solo puede hacer Pecera.

El texto viaja como FICHERO (se escribe, se sube con scp y allí se lee). Meterlo
en la línea de comandos de ssh es pedirle a dos shells seguidas que respeten las
comillas, los acentos y los signos de admiración de una frase en español, y una
de las dos siempre acaba rompiéndolo.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

RASPA = "roca@192.168.1.100"
CLAVE = "C:/Users/Roca/.ssh/roca"
PUERTO = "2222"
PIPER = "~/piper/piper/piper"
VOCES = {
    "sharvard": "~/piper/voices/es_ES-sharvard-medium.onnx",
    "davefx": "~/piper/voices/es_ES-davefx-medium.onnx",
}
VOZ_POR_DEFECTO = "sharvard"

_SSH = ["ssh", "-i", CLAVE, "-p", PUERTO, "-o", "ConnectTimeout=20",
        "-o", "StrictHostKeyChecking=accept-new", RASPA]
_SCP = ["scp", "-i", CLAVE, "-P", PUERTO, "-o", "ConnectTimeout=20",
        "-o", "StrictHostKeyChecking=accept-new"]


class SinVoz(RuntimeError):
    pass


def disponible() -> bool:
    try:
        r = subprocess.run(_SSH + [f"test -x {PIPER} && echo si"],
                           capture_output=True, text=True, timeout=30)
        return "si" in r.stdout
    except Exception:
        return False


def duracion(wav: Path) -> float:
    with wave.open(str(wav), "rb") as f:
        return f.getnframes() / float(f.getframerate())


def hablar(texto: str, destino: Path, voz: str = VOZ_POR_DEFECTO,
           trabajo: str = "estudio") -> Path:
    """Convierte una frase en un WAV. Devuelve el fichero local."""
    texto = (texto or "").strip()
    if not texto:
        raise SinVoz("no hay nada que decir")
    if voz not in VOCES:
        raise SinVoz(f"voz desconocida: {voz}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    local_txt = destino.with_suffix(".txt")
    local_txt.write_text(texto + "\n", encoding="utf-8")

    remoto = f"/tmp/kds_voz_{trabajo}_{destino.stem}"
    try:
        subprocess.run(_SCP + [str(local_txt), f"{RASPA}:{remoto}.txt"],
                       check=True, capture_output=True, timeout=60)
        orden = (f"{PIPER} --model {VOCES[voz]} --output_file {remoto}.wav "
                 f"< {remoto}.txt && echo LISTO")
        r = subprocess.run(_SSH + [orden], capture_output=True, text=True, timeout=180)
        if "LISTO" not in r.stdout:
            raise SinVoz(f"piper falló: {(r.stderr or r.stdout)[-300:]}")
        subprocess.run(_SCP + [f"{RASPA}:{remoto}.wav", str(destino)],
                       check=True, capture_output=True, timeout=120)
    finally:
        subprocess.run(_SSH + [f"rm -f {remoto}.txt {remoto}.wav"],
                       capture_output=True, timeout=30)

    if not destino.exists() or destino.stat().st_size < 1000:
        raise SinVoz("el WAV vino vacío")
    return destino


def _tiempo_srt(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int(round((segundos - int(segundos)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def subtitulos(tramos: list[tuple[float, float, str]], destino: Path) -> Path:
    """Un .srt a partir de (inicio, fin, texto).

    Se parte por comas y puntos cuando la frase es larga: un subtítulo de tres
    renglones no lo lee nadie mientras mira una pantalla de cocina.
    """
    lineas = []
    n = 0
    for inicio, fin, texto in tramos:
        texto = (texto or "").strip()
        if not texto:
            continue
        trozos = [texto]
        if len(texto) > 84:
            partes, actual = [], ""
            for cacho in texto.replace("; ", ". ").split(", "):
                if len(actual) + len(cacho) > 70 and actual:
                    partes.append(actual.strip(" ,"))
                    actual = cacho
                else:
                    actual = f"{actual}, {cacho}" if actual else cacho
            if actual:
                partes.append(actual.strip(" ,"))
            trozos = partes or [texto]

        paso = (fin - inicio) / len(trozos)
        for i, trozo in enumerate(trozos):
            n += 1
            a = inicio + paso * i
            b = min(a + paso, fin)
            lineas.append(f"{n}\n{_tiempo_srt(a)} --> {_tiempo_srt(b)}\n{trozo}\n")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino
