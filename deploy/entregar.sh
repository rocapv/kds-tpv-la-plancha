#!/usr/bin/env bash
# Deja una copia lista para entregar/enseñar en clase: código, documentación y volcado de la BD.
# Destino preferido D:\ProjecteIntermodular\KDS_TPV; si ese disco no admite escritura
# (es un USB con el exFAT dañado), cae a C:\ProjecteIntermodular\KDS_TPV.
set -euo pipefail
ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"
SOCKET="\$HOME/.local/share/kds-mariadb/kds.sock"

escribible() { mkdir -p "$1" 2>/dev/null && touch "$1/.prueba" 2>/dev/null && rm -f "$1/.prueba" 2>/dev/null; }

DESTINO=""
for candidato in "/d/ProjecteIntermodular/KDS_TPV" "/c/ProjecteIntermodular/KDS_TPV"; do
  if escribible "$candidato"; then DESTINO="$candidato"; break; fi
  echo "· $candidato no admite escritura, probando el siguiente"
done
[ -n "$DESTINO" ] || { echo "ERROR: ningún destino admite escritura"; exit 1; }

# robocopy /MIR deja el destino igual que el origen sin tener que borrar el árbol antes
robocopy "$(cygpath -w "$ORIGEN")" "$(cygpath -w "$DESTINO")" /MIR \
  /XD .git .venv __pycache__ entrega /NFL /NDL /NJH /NJS /NP >/dev/null || true

# Volcado de la base de datos tal y como está en la Mint
mkdir -p "$DESTINO/entrega"
ssh -o ConnectTimeout=10 mint "mariadb-dump --socket=$SOCKET --skip-ssl kds_tpv" \
  > "$DESTINO/entrega/kds_tpv_datos.sql" 2>/dev/null \
  || echo "· aviso: no se pudo volcar la BD (¿VM apagada?)"

{
  echo "KDS + TPV «La Plancha» — Proyecte Intermodular 1, 1º ASIR"
  echo "Copia generada el $(date '+%d/%m/%Y a las %H:%M')"
  echo
  echo "CONTENIDO"
  echo "  backend/      API FastAPI + SQL del esquema y los datos"
  echo "  frontend/     menú, TPV, KDS, facturación, carta, usuarios, ajustes e informe"
  echo "  deploy/       instalador, units de systemd y este script"
  echo "  docs/         documentación y mejoras pendientes"
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

echo "Entregado en $(cygpath -w "$DESTINO") ($(du -sh "$DESTINO" 2>/dev/null | cut -f1))"
