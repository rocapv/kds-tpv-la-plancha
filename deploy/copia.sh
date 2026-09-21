#!/usr/bin/env bash
# Copias de seguridad de kds_tpv: completa semanal + incremental por binlogs.
#
#   copia.sh completa      volcado íntegro y punto de partida para los incrementales
#   copia.sh incremental   cierra el binlog en curso y guarda los nuevos desde la última completa
#   copia.sh estado        qué hay guardado y cuánto ocupa
#
# Por qué binlogs y no un volcado diario entero: el volcado crece con la base de datos y
# se repite casi igual cada día; el binlog solo contiene lo que ha cambiado desde el corte
# anterior, así que una incremental de un día de servicio ocupa kilobytes y permite
# recuperar hasta el último minuto antes del fallo (point-in-time recovery).
set -euo pipefail

DESTINO="${KDS_COPIAS:-$HOME/copias/kds_tpv}"
SOCKET="${KDS_DB_SOCKET:-$HOME/.local/share/kds-mariadb/kds.sock}"
BD="${KDS_DB_NAME:-kds_tpv}"
SEMANAS_A_GUARDAR=4

mkdir -p "$DESTINO/completas" "$DESTINO/incrementales"
cliente() { mariadb --socket="$SOCKET" --skip-ssl "$@"; }
registrar() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$DESTINO/copias.log"; }

directorio_binlogs() {
  cliente -N -B -e "SELECT @@log_bin_basename" 2>/dev/null | head -1 | xargs -r dirname
}

copia_completa() {
  local marca archivo
  marca="$(date '+%Y%m%d-%H%M')"
  archivo="$DESTINO/completas/$BD-$marca.sql.gz"
  # --single-transaction: copia coherente sin bloquear el servicio (InnoDB)
  # --flush-logs + --master-data=2: abre un binlog nuevo y anota la posición exacta,
  #   de modo que los incrementales posteriores arrancan justo donde acaba esta copia.
  mariadb-dump --socket="$SOCKET" --skip-ssl \
    --single-transaction --flush-logs --master-data=2 --routines --events \
    "$BD" | gzip -6 > "$archivo"
  # el punto de partida queda guardado junto a la copia
  zcat "$archivo" | grep -m1 "CHANGE MASTER TO" > "$DESTINO/completas/$BD-$marca.posicion" || true
  date +%s > "$DESTINO/completas/$BD-$marca.momento"
  registrar "completa $archivo ($(du -h "$archivo" | cut -f1))"
  echo "· copia completa: $archivo ($(du -h "$archivo" | cut -f1))"
  podar
}

copia_incremental() {
  local dir_binlogs ultima_completa copiados=0
  dir_binlogs="$(directorio_binlogs)"
  if [ -z "$dir_binlogs" ]; then
    echo "ERROR: el servidor no tiene binlog activado (log_bin). Revisa my.cnf." >&2
    exit 2
  fi
  ultima_completa="$(ls -t "$DESTINO/completas/"*.momento 2>/dev/null | head -1)"
  if [ -z "$ultima_completa" ]; then
    echo "· no hay copia completa todavía: hago una primero"
    copia_completa
    return
  fi
  # Cerrar el binlog en curso: lo que ya está cerrado no volverá a cambiar y se puede copiar.
  cliente -e "FLUSH BINARY LOGS"
  local actual
  actual="$(cliente -N -B -e "SHOW BINARY LOGS" | tail -1 | awk '{print $1}')"
  while read -r binlog; do
    [ -n "$binlog" ] || continue
    [ "$(basename "$binlog")" = "$actual" ] && continue          # el activo aún puede crecer
    [ "$binlog" -nt "$ultima_completa" ] || continue             # anterior a la última completa
    local destino="$DESTINO/incrementales/$(basename "$binlog").gz"
    [ -f "$destino" ] && continue                                # ya guardado
    gzip -6 -c "$binlog" > "$destino"
    copiados=$((copiados + 1))
  done < <(find "$dir_binlogs" -maxdepth 1 -name '*-bin.[0-9]*' | sort)
  registrar "incremental: $copiados binlogs nuevos"
  echo "· incremental: $copiados binlog(s) nuevos en $DESTINO/incrementales"
}

podar() {
  # Se conservan las N últimas completas; los binlogs anteriores a la más antigua ya no
  # sirven para nada, porque no hay copia completa a la que aplicarlos.
  local sobran
  mapfile -t sobran < <(ls -t "$DESTINO/completas/"*.sql.gz 2>/dev/null | tail -n +$((SEMANAS_A_GUARDAR + 1)))
  for f in "${sobran[@]:-}"; do
    [ -n "$f" ] || continue
    rm -f "$f" "${f%.sql.gz}.posicion" "${f%.sql.gz}.momento"
    registrar "podada $f"
  done
  local mas_antigua
  mas_antigua="$(ls -t "$DESTINO/completas/"*.momento 2>/dev/null | tail -1)"
  [ -n "$mas_antigua" ] || return 0
  find "$DESTINO/incrementales" -name '*.gz' ! -newer "$mas_antigua" -delete
}

estado() {
  echo "Copias en $DESTINO"
  echo
  echo "Completas:"
  ls -lh "$DESTINO/completas/"*.sql.gz 2>/dev/null | awk '{print "  " $9 "  " $5}' || echo "  (ninguna)"
  echo "Incrementales:"
  ls -lh "$DESTINO/incrementales/"*.gz 2>/dev/null | awk '{print "  " $9 "  " $5}' | tail -8 || echo "  (ninguna)"
  echo
  echo "Ocupación total: $(du -sh "$DESTINO" 2>/dev/null | cut -f1)"
  echo "Última restauración probada: $(grep -m1 'restauracion OK' <(tac "$DESTINO/copias.log" 2>/dev/null) || echo 'nunca')"
}

case "${1:-estado}" in
  completa)    copia_completa ;;
  incremental) copia_incremental ;;
  estado)      estado ;;
  *) echo "uso: $0 {completa|incremental|estado}" >&2; exit 1 ;;
esac
