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
# Ampliaciones: se pueden aplicar sobre una BD ya en uso
for ampliacion in sql/0[3-9]_*.sql; do
  echo "· Aplicando $(basename "$ampliacion")"
  mariadb kds_tpv < "$ampliacion" || true
done

echo "· Certificado TLS"
bash "$DIR/deploy/certificado.sh"

mkdir -p ~/.config/systemd/user
for u in kds-tpv kds-tpv-http; do
  sed "s#@DIR@#$DIR#g" "$DIR/deploy/$u.service" > ~/.config/systemd/user/$u.service
done
systemctl --user daemon-reload
systemctl --user enable --now kds-tpv.service kds-tpv-http.service
systemctl --user restart kds-tpv.service kds-tpv-http.service
sleep 3
IP="$(hostname -I | awk '{print $1}')"
curl -fsSk https://localhost:8443/api/salud && echo
echo "OK · https://$IP:8443/   (el puerto 8090 redirige aquí)"
