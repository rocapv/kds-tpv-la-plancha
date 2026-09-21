#!/usr/bin/env bash
# Deja en D:\ProjecteIntermodular\KDS_TPV una copia lista para entregar/enseñar en clase:
# el código, la documentación y un volcado de la base de datos con los datos de la demo.
set -euo pipefail
ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="/d/ProjecteIntermodular/KDS_TPV"
SOCKET="\$HOME/.local/share/kds-mariadb/kds.sock"

rm -rf "$DESTINO"
mkdir -p "$DESTINO"
# Código fuente sin entornos virtuales ni historial de git
tar cf - --exclude=.git --exclude=.venv --exclude=__pycache__ -C "$ORIGEN" . | tar xf - -C "$DESTINO"

# Volcado de la base de datos tal y como está en la Mint
mkdir -p "$DESTINO/entrega"
ssh mint "mariadb-dump --socket=$SOCKET --skip-ssl kds_tpv" > "$DESTINO/entrega/kds_tpv_datos.sql" 2>/dev/null \
  || echo "· aviso: no se pudo volcar la BD (¿servidor parado?)"

{
  echo "KDS + TPV «La Plancha» — Proyecte Intermodular 1, 1º ASIR"
  echo "Copia generada el $(date '+%d/%m/%Y a las %H:%M')"
  echo
  echo "CONTENIDO"
  echo "  backend/      API FastAPI + SQL del esquema y los datos"
  echo "  frontend/     TPV, KDS, facturación, usuarios, ajustes e informe"
  echo "  deploy/       instalador, unit de systemd y este script"
  echo "  docs/         documentación del proyecto"
  echo "  entrega/      volcado de la base de datos de la demo"
  echo
  echo "PARA ARRANCARLO EN UN LINUX NUEVO"
  echo "  sudo apt install -y mariadb-server python3-venv"
  echo "  sudo mariadb < deploy/00_crear_bd.sql"
  echo "  bash deploy/instalar.sh"
  echo "  Navegador: http://<ip>:8090/"
  echo
  echo "DEMO EN MARCHA (aula): http://192.168.1.105:8090/"
  echo "PIN: Laura 1111 · Marc 2222 · Aitana 3333 · Pau 9999 (encargado)"
} > "$DESTINO/LEEME.txt"

echo "Entregado en D:\\ProjecteIntermodular\\KDS_TPV ($(du -sh "$DESTINO" | cut -f1))"
