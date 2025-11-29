#!/usr/bin/env bash
# Добавляет пира в /etc/wireguard/wg0.conf и применяет конфиг.
# Аргументы: PUBLIC_KEY ALLOWED_IPS [PRESHARED_KEY] [ENDPOINT_IP]
# Требует: root, wireguard-tools, готовый wg0.conf.
set -euo pipefail

WG_IFACE="${WG_IFACE:-wg0}"
CFG_PATH="/etc/wireguard/${WG_IFACE}.conf"
PERSISTENT_KEEPALIVE="${WG_PERSISTENT_KEEPALIVE:-25}"

PUBLIC_KEY="${1:-}"
ALLOWED_IPS="${2:-}"
PRESHARED="${3:-}"
ENDPOINT_IP="${4:-}" # опционально для site-to-site

log() { printf '[WG-PEER] %s\n' "$*"; }

if [[ -z "$PUBLIC_KEY" || -z "$ALLOWED_IPS" ]]; then
  log "Использование: WG_IFACE=wg0 $0 PUBLIC_KEY ALLOWED_IPS [PRESHARED] [ENDPOINT_IP]"
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  log "Запустите от root (sudo)"; exit 1;
fi

if [[ ! -f "$CFG_PATH" ]]; then
  log "Конфиг ${CFG_PATH} не найден. Сначала запустите wg_server_init.sh"
  exit 1
fi

{
  echo ""
  echo "[Peer]"
  echo "PublicKey = ${PUBLIC_KEY}"
  [[ -n "$PRESHARED" ]] && echo "PresharedKey = ${PRESHARED}"
  [[ -n "$ENDPOINT_IP" ]] && echo "Endpoint = ${ENDPOINT_IP}"
  echo "AllowedIPs = ${ALLOWED_IPS}"
  echo "PersistentKeepalive = ${PERSISTENT_KEEPALIVE}"
} >> "$CFG_PATH"

log "Пир добавлен в ${CFG_PATH}"

wg syncconf "$WG_IFACE" <(wg-quick strip "$WG_IFACE")
log "Конфиг применён: wg syncconf ${WG_IFACE}"
