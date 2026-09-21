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

# robocopy /MIR deja el destino igual que el origen sin tener que borrar el arbol antes.
# MSYS_NO_PATHCONV=1 es imprescindible: sin el, Git Bash convierte /MIR en una ruta
# ("C:/Program Files/Git/MIR") y robocopy aborta sin copiar nada.
MSYS_NO_PATHCONV=1 robocopy "$(cygpath -w "$ORIGEN")" "$(cygpath -w "$DESTINO")" /MIR /XD .git .venv __pycache__ entrega /NFL /NDL /NJH /NJS /NP >/dev/null && RC=0 || RC=$?
# robocopy devuelve 0-7 como exito; >=8 es error real
[ "$RC" -lt 8 ] || { echo "ERROR: robocopy fallo con codigo $RC"; exit 1; }

# Volcado de la base de datos tal y como está en la Mint
mkdir -p "$DESTINO/entrega"
ssh -o ConnectTimeout=10 mint "mariadb-dump --socket=$SOCKET --skip-ssl kds_tpv" \
  > "$DESTINO/entrega/kds_tpv_datos.sql" 2>/dev/null \
  || echo "· aviso: no se pudo volcar la BD (¿VM apagada?)"

{
  echo "KDS + TPV «Cantina Vesta-9» — Proyecte Intermodular 1, 1º ASIR"
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

N=$(find "$DESTINO" -type f | wc -l)
[ "$N" -ge 20 ] || { echo "ERROR: solo $N ficheros en el destino, la copia esta incompleta"; exit 1; }
[ -s "$DESTINO/entrega/kds_tpv_datos.sql" ] || { echo "ERROR: el volcado de la BD esta vacio"; exit 1; }

echo "Entregado en $(cygpath -w "$DESTINO") - $N ficheros, $(du -sh "$DESTINO" 2>/dev/null | cut -f1)"
