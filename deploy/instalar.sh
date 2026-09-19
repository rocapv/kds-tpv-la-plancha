#!/usr/bin/env bash
# Instala / actualiza KDS+TPV en la Mint como servicio de usuario (sin sudo).
# Requisito previo (una vez, con sudo):  sudo mariadb < deploy/00_crear_bd.sql
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR/backend"

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

if [ "${1:-}" = "--reset-bd" ] || ! mariadb kds_tpv -e "SELECT 1 FROM empleados LIMIT 1" >/dev/null 2>&1; then
  echo "· Cargando esquema y datos de ejemplo"
  mariadb kds_tpv < sql/01_schema.sql
  mariadb kds_tpv < sql/02_seed.sql
fi

mkdir -p ~/.config/systemd/user
sed "s#@DIR@#$DIR#g" "$DIR/deploy/kds-tpv.service" > ~/.config/systemd/user/kds-tpv.service
systemctl --user daemon-reload
systemctl --user enable --now kds-tpv.service
systemctl --user restart kds-tpv.service
sleep 2
curl -fsS http://localhost:8090/api/salud && echo && echo "OK · http://$(hostname -I | awk '{print $1}'):8090/"
