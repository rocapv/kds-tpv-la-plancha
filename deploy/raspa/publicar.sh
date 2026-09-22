#!/usr/bin/env bash
# Publica el frontal del KDS en el document root de Apache (RASPA).
#
#   bash deploy/raspa/publicar.sh
#
# En la Mint el frontal lo servía la propia aplicación, que sustituía `__V__` por la fecha del
# CSS/JS más reciente al vuelo. Aquí lo sirve Apache, que no sustituye nada: si se dejara el
# `__V__` literal, la URL de cada recurso no cambiaría NUNCA y el navegador se quedaría con el
# JavaScript viejo para siempre (esa caché ya ha engañado a este proyecto tres veces en una
# tarde). Por eso el sello se pone aquí, al publicar.
set -euo pipefail
ORIGEN="${1:-$HOME/kds_tpv/frontend}"
DESTINO="${2:-/var/www/html}"
SELLO="$(date +%Y%m%d%H%M%S)"

[ -f "$ORIGEN/index.html" ] || { echo "ERROR: $ORIGEN no parece el frontal del KDS"; exit 1; }

# --delete deja el destino igual que el origen. Se salva .well-known: ahí contesta Let's
# Encrypt para renovar los certificados de esta máquina y no es cosa del KDS.
sudo rsync -a --delete --exclude '.well-known' "$ORIGEN"/ "$DESTINO"/

# El sello de versión, solo en las páginas (es donde está el `?v=__V__`).
sudo find "$DESTINO" -maxdepth 1 -name '*.html' -exec sed -i "s/__V__/$SELLO/g" {} +

sudo chown -R root:www-data "$DESTINO"
sudo find "$DESTINO" -type d -exec chmod 755 {} +
sudo find "$DESTINO" -type f -exec chmod 644 {} +

echo "Publicado en $DESTINO · sello $SELLO · $(sudo find "$DESTINO" -type f | wc -l) ficheros"
