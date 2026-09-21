#!/usr/bin/env bash
# Restauración de kds_tpv y prueba automática de que la copia sirve.
#
#   restaurar.sh probar              restaura en una BD de prueba y compara filas (no toca la buena)
#   restaurar.sh real --si-de-verdad restaura ENCIMA de la base real (pide confirmación explícita)
#
# Una copia que nunca se ha restaurado no es una copia: es un fichero.
set -euo pipefail

DESTINO="${KDS_COPIAS:-$HOME/copias/kds_tpv}"
SOCKET="${KDS_DB_SOCKET:-$HOME/.local/share/kds-mariadb/kds.sock}"
BD="${KDS_DB_NAME:-kds_tpv}"
BD_PRUEBA="${BD}_prueba"

cliente() { mariadb --socket="$SOCKET" --skip-ssl "$@"; }
registrar() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$DESTINO/copias.log"; }

ultima_completa() { ls -t "$DESTINO/completas/"*.sql.gz 2>/dev/null | head -1; }

restaurar_en() {
  local destino_bd="$1" completa
  completa="$(ultima_completa)"
  [ -n "$completa" ] || { echo "ERROR: no hay ninguna copia completa" >&2; exit 2; }
  echo "· copia completa: $(basename "$completa")"
  cliente -e "DROP DATABASE IF EXISTS \`$destino_bd\`; CREATE DATABASE \`$destino_bd\` CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci"
  zcat "$completa" | cliente "$destino_bd"

  # Y encima, todo lo que pasó después: los binlogs guardados como incrementales.
  local aplicados=0
  for inc in $(ls "$DESTINO/incrementales/"*.gz 2>/dev/null | sort); do
    [ "$inc" -nt "${completa%.sql.gz}.momento" ] || continue
    zcat "$inc" | mariadb-binlog --database="$BD" - 2>/dev/null \
      | sed "s/\`$BD\`/\`$destino_bd\`/g; s/^USE \`\?$BD\`\?/USE \`$destino_bd\`/" \
      | cliente "$destino_bd" 2>/dev/null || true
    aplicados=$((aplicados + 1))
  done
  echo "· incrementales aplicados: $aplicados"
}

probar() {
  restaurar_en "$BD_PRUEBA"
  echo
  printf '%-16s %10s %10s\n' TABLA ORIGINAL RESTAURADA
  local fallos=0
  for t in empleados mesas categorias productos pedidos lineas_pedido pagos facturas; do
    local a b
    a="$(cliente -N -B -e "SELECT COUNT(*) FROM \`$BD\`.$t" 2>/dev/null || echo "-")"
    b="$(cliente -N -B -e "SELECT COUNT(*) FROM \`$BD_PRUEBA\`.$t" 2>/dev/null || echo "-")"
    printf '%-16s %10s %10s %s\n' "$t" "$a" "$b" "$([ "$a" = "$b" ] && echo OK || { echo DIFIERE; })"
    [ "$a" = "$b" ] || fallos=$((fallos + 1))
  done
  # Comprobación de negocio: el dinero cobrado debe coincidir exactamente
  local ca cb
  ca="$(cliente -N -B -e "SELECT COALESCE(SUM(importe_cent),0) FROM \`$BD\`.pagos")"
  cb="$(cliente -N -B -e "SELECT COALESCE(SUM(importe_cent),0) FROM \`$BD_PRUEBA\`.pagos")"
  printf '%-16s %10s %10s %s\n' "€ cobrado" "$ca" "$cb" "$([ "$ca" = "$cb" ] && echo OK || echo DIFIERE)"
  [ "$ca" = "$cb" ] || fallos=$((fallos + 1))

  cliente -e "DROP DATABASE \`$BD_PRUEBA\`"
  if [ "$fallos" -eq 0 ]; then
    registrar "restauracion OK ($(basename "$(ultima_completa)"))"
    echo; echo "RESTAURACIÓN CORRECTA: la copia sirve."
  else
    registrar "restauracion FALLIDA: $fallos diferencias"
    echo; echo "ATENCIÓN: $fallos diferencias. La copia NO es fiable." >&2
    exit 1
  fi
}

case "${1:-probar}" in
  probar) probar ;;
  real)
    [ "${2:-}" = "--si-de-verdad" ] || { echo "Esto machaca la base real. Repite con: $0 real --si-de-verdad" >&2; exit 1; }
    restaurar_en "$BD"
    registrar "RESTAURACION REAL sobre $BD"
    echo "· restaurada la base real"
    ;;
  *) echo "uso: $0 {probar|real --si-de-verdad}" >&2; exit 1 ;;
esac
