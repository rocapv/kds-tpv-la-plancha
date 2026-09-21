#!/usr/bin/env bash
# Cortafuegos del servidor: el KDS+TPV solo se atiende desde la red local.
# Necesita root, así que se ejecuta aparte del instalador:
#
#   sudo bash deploy/cortafuegos.sh              # aplica las reglas
#   sudo bash deploy/cortafuegos.sh --estado     # las enseña
#
# La aplicación ya rechaza por su cuenta a quien no sea de la LAN; esto añade la capa de red,
# que es la que hay que tener: lo que no llega al proceso no puede fallar en el proceso.
set -euo pipefail
RED="${KDS_RED:-192.168.1.0/24}"

[ "$(id -u)" = "0" ] || { echo "Ejecuta con sudo" >&2; exit 1; }

if [ "${1:-}" = "--estado" ]; then
  ufw status verbose
  exit 0
fi

ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow from "$RED" to any port 22   proto tcp comment 'SSH solo desde la LAN'
ufw allow from "$RED" to any port 8443 proto tcp comment 'KDS+TPV HTTPS'
ufw allow from "$RED" to any port 8090 proto tcp comment 'Redireccion a HTTPS'
# MariaDB no se abre a nadie: la aplicación entra por socket Unix.
ufw deny 3306/tcp comment 'MariaDB: solo socket local'
ufw --force enable
ufw status verbose
