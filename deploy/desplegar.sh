#!/usr/bin/env bash
# Despliegue con red de seguridad: copia → pruebas → reinicio → comprobación.
# Si las pruebas fallan, el servicio en marcha NO se toca.
#
#   desplegar.sh              despliega si las pruebas pasan
#   desplegar.sh --sin-copia  salta la copia previa (solo en pruebas)
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR/backend"

echo "══ 1/4 · Copia de seguridad previa"
if [ "${1:-}" = "--sin-copia" ]; then
  echo "· saltada a petición"
else
  bash "$DIR/deploy/copia.sh" incremental
fi

echo "══ 2/4 · Dependencias"
.venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt

echo "══ 3/4 · Pruebas automáticas (sobre una BD de pruebas, no la real)"
if ! .venv/bin/python -m pytest; then
  echo
  echo "✋ DESPLIEGUE ABORTADO: las pruebas no pasan. El servicio sigue con la versión anterior."
  exit 1
fi

echo "══ 4/4 · Reinicio y comprobación"
systemctl --user restart kds-tpv.service kds-tpv-http.service
sleep 3
for intento in 1 2 3 4 5; do
  if curl -fsSk https://localhost:8443/api/salud >/dev/null; then
    echo "· servicio arriba"
    systemctl --user is-active kds-mariadb kds-tpv kds-tpv-http
    echo "DESPLEGADO · https://$(hostname -I | awk '{print $1}'):8443/"
    exit 0
  fi
  sleep 2
done
echo "✋ El servicio no responde tras el reinicio. Revisa: journalctl --user -u kds-tpv -n 50" >&2
exit 1
