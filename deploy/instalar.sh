#!/usr/bin/env bash
# Instala / actualiza KDS+TPV en la Mint como servicio de usuario (sin sudo).
# Requisito previo (una vez, con sudo):  sudo mariadb < deploy/00_crear_bd.sql
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR/backend"

# MariaDB propia del usuario (servicio kds-mariadb): hay que hablarle por su socket.
# Si no existe, se usa la del sistema. Sin esto las ampliaciones se aplicaban «en el aire»
# (el for de abajo lleva `|| true`) y el decorado o las migraciones no llegaban a la BD.
SOCK="${KDS_DB_SOCKET:-$HOME/.local/share/kds-mariadb/kds.sock}"
if [ -S "$SOCK" ]; then
  MARIADB=(mariadb --socket="$SOCK" -u "${KDS_DB_USER:-$USER}")
else
  MARIADB=(mariadb)
fi

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

if [ "${1:-}" = "--reset-bd" ] || ! "${MARIADB[@]}" kds_tpv -e "SELECT 1 FROM empleados LIMIT 1" >/dev/null 2>&1; then
  echo "· Cargando esquema y datos de ejemplo"
  "${MARIADB[@]}" kds_tpv < sql/01_schema.sql
  "${MARIADB[@]}" kds_tpv < sql/02_seed.sql
fi
# Ampliaciones: se pueden aplicar sobre una BD ya en uso
for ampliacion in sql/[0-9][0-9]_*.sql; do
  case "$(basename "$ampliacion")" in 0[12]_*) continue;; esac
  echo "· Aplicando $(basename "$ampliacion")"
  "${MARIADB[@]}" kds_tpv < "$ampliacion" || echo "  ! falló $(basename "$ampliacion")"
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
