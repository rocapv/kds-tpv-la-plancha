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

if ! curl -fsS --max-time 10 http://127.0.0.1:8092/api/salud >/dev/null; then
  echo "✋ la API no responde tras actualizar" >&2
  deshacer
fi

echo "ACTUALIZADO · $(git log --oneline -1)"
