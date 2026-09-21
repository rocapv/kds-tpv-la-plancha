#!/usr/bin/env bash
# Certificado autofirmado para la demo (en producción: certificado de una CA, o Let's Encrypt).
# Incluye la IP de la máquina en subjectAltName: sin eso, los navegadores modernos no lo aceptan.
# Va marcado CA:FALSE a propósito: se puede instalar como excepción de confianza en un equipo de
# clase sin que sirva para firmar certificados de otros sitios si la clave llegara a perderse.
set -euo pipefail
# --rehacer vale en cualquier posición; el otro argumento es el directorio del certificado.
REHACER=no; DIR=""
for arg in "$@"; do
  case "$arg" in --rehacer) REHACER=si;; *) DIR="$arg";; esac
done
DIR="${DIR:-$HOME/.local/share/kds-tpv/certs}"
IP="$(hostname -I | awk '{print $1}')"
mkdir -p "$DIR"
if [ -f "$DIR/cert.pem" ] && [ "$REHACER" = no ]; then
  echo "· ya existe $DIR/cert.pem (usa --rehacer para regenerarlo)"
  openssl x509 -in "$DIR/cert.pem" -noout -subject -enddate
  exit 0
fi
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout "$DIR/key.pem" -out "$DIR/cert.pem" \
  -subj "/C=ES/ST=Valencia/L=Burjassot/O=Cantina Vesta-9/CN=kds.local" \
  -addext "subjectAltName=DNS:kds.local,DNS:localhost,IP:$IP,IP:127.0.0.1" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth" 2>/dev/null
chmod 600 "$DIR/key.pem"
echo "· certificado nuevo para kds.local / $IP"
openssl x509 -in "$DIR/cert.pem" -noout -subject -enddate -ext basicConstraints
