#!/usr/bin/env bash
# Trae lo nuevo del repo y lo pone en marcha. Lo llama `kds-actualiza.timer` cada 5 minutos.
#
#   bash deploy/raspa/actualizar.sh          se actualiza si hay algo nuevo
#   bash deploy/raspa/actualizar.sh --forzar  reaplica aunque no haya commits nuevos
#
# Tres cosas que este guion NO hace, a propósito:
#   · No pisa trabajo hecho en Raspa. Si hay cambios sin commitear, se para y lo dice. Quien
#     esté editando aquí no se encuentra su fichero reescrito a mitad de frase.
#   · No fuerza la rama. Solo avanza en línea recta (--ff-only); si el historial ha divergido,
#     eso lo mira una persona.
#   · No despliega nada que no pase las pruebas. Si fallan, deshace el avance y deja el
#     servicio con la versión de antes, que es la que se sabe que funcionaba.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RAMA="${KDS_RAMA:-ASIR-KDS-TPV}"
export KDS_DB_SOCKET="${KDS_DB_SOCKET:-/run/mysqld/mysqld.sock}"
cd "$DIR"

ANTES="$(git rev-parse HEAD)"
git fetch -q origin "$RAMA"
NUEVO="$(git rev-parse "origin/$RAMA")"

if [ "$ANTES" = "$NUEVO" ] && [ "${1:-}" != "--forzar" ]; then
  echo "sin novedad · ${ANTES:0:7}"
  exit 0
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "✋ hay cambios sin commitear en $DIR; no toco nada" >&2
  git status --short >&2
  exit 1
fi

git merge --ff-only -q "origin/$RAMA" || { echo "✋ la rama ha divergido, hace falta una persona" >&2; exit 1; }
CAMBIADOS="$(git diff --name-only "$ANTES" HEAD)"
echo "== ${ANTES:0:7} → ${NUEVO:0:7} · $(echo "$CAMBIADOS" | grep -c . ) ficheros"

deshacer() {
  echo "✋ deshaciendo: vuelvo a ${ANTES:0:7}" >&2
  git reset -q --hard "$ANTES"
  # Si ya se había publicado o reiniciado, hay que devolver también lo que está sirviendo.
  bash deploy/raspa/publicar.sh >/dev/null 2>&1 || true
  sudo systemctl restart kds-tpv || true
  exit 1
}

# 1 · Dependencias, solo si han cambiado
if echo "$CAMBIADOS" | grep -q '^backend/requirements'; then
  echo "· dependencias"
  backend/.venv/bin/pip install -q -r backend/requirements.txt || deshacer
fi

# 2 · Pruebas, siempre que se toque el backend. Corren sobre una base efímera, nunca la real.
if echo "$CAMBIADOS" | grep -qE '^backend/(app|sql|pruebas)/'; then
  echo "· pruebas"
  backend/.venv/bin/pip install -q -r backend/requirements-dev.txt >/dev/null 2>&1 || true
  ( cd backend && .venv/bin/python -m pytest -q ) || deshacer
fi

# 3 · Ampliaciones del esquema que falten
if echo "$CAMBIADOS" | grep -q '^backend/sql/'; then
  echo "· esquema"
  bash deploy/raspa/migrar.sh || deshacer
fi

# 4 · Pantallas (con su sello de versión, que Apache no lo pone)
if echo "$CAMBIADOS" | grep -qE '^frontend/'; then
  echo "· pantallas"
  bash deploy/raspa/publicar.sh
  # El sitio de pruebas de la LAN (:8093) sirve OTRA copia del frontal y nadie la republicaba:
  # se quedó congelada el 28/09. Contra esa copia corren el QA del cliente y las capturas de los
  # vídeos, así que llevaban días dando por bueno código viejo y culpando al nuevo de fallos que
  # ya estaban arreglados. Una copia de pruebas que no se actualiza no avisa: miente. O se
  # publica junto con la de producción, o no tiene sentido tenerla.
  if [ -d /var/www/kds_pruebas ]; then
    echo "· pantallas del sitio de pruebas (:8093)"
    bash deploy/raspa/publicar.sh "$DIR/frontend" /var/www/kds_pruebas
  fi
fi

# 5 · La API, si ha cambiado su código
if echo "$CAMBIADOS" | grep -qE '^backend/(app|requirements)'; then
  echo "· reiniciando la API"
  sudo systemctl restart kds-tpv
  sleep 3
fi

# 6 · Configuración de Apache: se avisa, pero NO se instala sola. Tocar el servidor web de
#     Raspa afecta a Jellyfin, al Director y a todo lo demás que vive ahí.
if echo "$CAMBIADOS" | grep -qE '^deploy/raspa/.*\.conf$'; then
  echo "⚠ han cambiado vhosts de Apache en el repo; revísalos e instálalos a mano:"
  echo "$CAMBIADOS" | grep -E '^deploy/raspa/.*\.conf$' | sed 's/^/    /'
fi

# La comprobación de salud REINTENTA. Con un solo intento, en un Pi cargado el arranque tarda
# más que la espera y se deshacía un despliegue que estaba perfectamente: el remedio era peor
# que la enfermedad, porque la vuelta atrás reinicia el servicio OTRA vez y tira las sesiones
# de quien esté trabajando (pasó el 28/09 con alguien conectado desde fuera).
sano=0
for intento in 1 2 3 4 5 6; do
  if curl -fsS --max-time 8 http://127.0.0.1:8092/api/salud >/dev/null; then sano=1; break; fi
  sleep 3
done
if [ "$sano" != "1" ]; then
  echo "✋ la API no responde tras actualizar (6 intentos en ~30 s)" >&2
  deshacer
fi

echo "ACTUALIZADO · $(git log --oneline -1)"
