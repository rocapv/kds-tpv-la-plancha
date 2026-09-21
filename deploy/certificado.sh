#!/usr/bin/env bash
# Certificado autofirmado para la demo (en producción: certificado de una CA, o Let's Encrypt).
# Incluye la IP de la máquina en subjectAltName: sin eso, los navegadores modernos no lo aceptan.
set -euo pipefail
DIR="${1:-$HOME/.local/share/kds-tpv/certs}"
IP="$(hostname -I | awk '{print $1}')"
mkdir -p "$DIR"
if [ -f "$DIR/cert.pem" ] && ! [ "${2:-}" = "--rehacer" ]; then
  echo "· ya existe $DIR/cert.pem (usa --rehacer para regenerarlo)"
  openssl x509 -in "$DIR/cert.pem" -noout -subject -enddate
  exit 0
fi
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout "$DIR/key.pem" -out "$DIR/cert.pem" \
  -subj "/C=ES/ST=Valencia/L=Burjassot/O=La Plancha/CN=kds.local" \
  -addext "subjectAltName=DNS:kds.local,DNS:localhost,IP:$IP,IP:127.0.0.1" \
  -addext "keyUsage=digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth" 2>/dev/null
chmod 600 "$DIR/key.pem"
echo "· certificado nuevo para kds.local / $IP"
openssl x509 -in "$DIR/cert.pem" -noout -subject -enddate
