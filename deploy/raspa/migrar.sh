#!/usr/bin/env bash
# Aplica las ampliaciones de backend/sql/ que todavía no estén puestas en esta base.
#
# La regla del proyecto es que cada cambio del esquema es un fichero numerado nuevo, nunca una
# edición del anterior. Aquí se lleva la cuenta en una tabla `migraciones`: lo que ya está
# apuntado no se vuelve a ejecutar.
#
# DOS FICHEROS NO SE APLICAN NUNCA de forma automática:
#   · 01_schema.sql  →  empieza con DROP TABLE. Ejecutarlo sería borrar el servicio del día.
#   · 02_seed.sql    →  son datos de ejemplo; en un local de verdad no pintan nada.
# La primera vez que corre, en una base que ya existe, se limita a APUNTAR lo que hay como ya
# aplicado: si no, creería que tiene que instalar el sistema entero encima de él mismo.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BD="${KDS_DB_NAME:-kds_tpv}"
MARIADB=(mariadb --skip-ssl "$BD")

"${MARIADB[@]}" -e "CREATE TABLE IF NOT EXISTS migraciones (
  fichero   VARCHAR(120) NOT NULL PRIMARY KEY,
  aplicada  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB"

# ¿Base recién montada o base en marcha? Si ya hay pedidos, esto no es una instalación.
YA_VIVA=$("${MARIADB[@]}" -N -B -e "SELECT COUNT(*) FROM information_schema.tables
                                   WHERE table_schema='$BD' AND table_name='pedidos'")
PRIMERA=$("${MARIADB[@]}" -N -B -e "SELECT COUNT(*) FROM migraciones")

nuevas=0
for guion in "$DIR"/backend/sql/*.sql; do
  nombre="$(basename "$guion")"
  case "$nombre" in 01_schema.sql|02_seed.sql) continue;; esac
  puesta=$("${MARIADB[@]}" -N -B -e "SELECT COUNT(*) FROM migraciones WHERE fichero='$nombre'")
  [ "$puesta" = "1" ] && continue

  # Antes, la primera vez sobre una base ya en marcha se apuntaba TODO como aplicado sin
  # ejecutarlo. Parecía prudente y salió caro: `14_imagenes.sql` estaba en el repo pero sus
  # tablas nunca se habían creado, así que quedó marcado como aplicado y el día que algo las
  # necesitó, no existían. Ahora se ejecutan todas: son idempotentes a propósito (CREATE TABLE
  # IF NOT EXISTS, ADD COLUMN IF NOT EXISTS, INSERT IGNORE) y las dos únicas que no lo son
  # —01_schema, que empieza con DROP, y 02_seed— están excluidas más arriba.
  echo "· aplicando $nombre"
  "${MARIADB[@]}" < "$guion"
  "${MARIADB[@]}" -e "INSERT IGNORE INTO migraciones (fichero) VALUES ('$nombre')"
  nuevas=$((nuevas + 1))
done

echo "ampliaciones aplicadas: $nuevas"
[ "$YA_VIVA" = "1" ] || echo "(base nueva)"
