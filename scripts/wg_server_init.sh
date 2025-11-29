#!/usr/bin/env bash
# Генерирует серверные ключи и черновой /etc/wireguard/wg0.conf.
# Не перезаписывает существующий wg0.conf (делает бэкап, если файл есть).
# Требует: wireguard-tools, bash, root.
set -euo pipefail

WG_IFACE="${WG_IFACE:-wg0}"
WG_PORT="${WG_PORT:-51820}"
WG_ADDRESS="${WG_ADDRESS:-10.8.0.1/24}"
WG_ALLOWED_IPS="${WG_ALLOWED_IPS:-0.0.0.0/0,::/0}"
WG_DNS="${WG_DNS:-1.1.1.1}"
WG_PERSISTENT_KEEPALIVE="${WG_PERSISTENT_KEEPALIVE:-25}"

CFG_PATH="/etc/wireguard/${WG_IFACE}.conf"
KEY_DIR="/etc/wireguard"

log() { printf '[WG-INIT] %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  log "Запустите от root (sudo)"; exit 1;
fi

mkdir -p "$KEY_DIR"
cd "$KEY_DIR"

if [[ -f server_private.key || -f server_public.key ]]; then
  log "Ключи уже существуют, пропускаю генерацию."
else
  umask 077
  wg genkey | tee server_private.key | wg pubkey > server_public.key
  log "Серверные ключи сгенерированы."
fi

SERVER_PRIV=$(cat server_private.key)
SERVER_PUB=$(cat server_public.key)

if [[ -f "$CFG_PATH" ]]; then
  cp "$CFG_PATH" "${CFG_PATH}.$(date +%s).bak"
  log "Существующий ${CFG_PATH} сохранён в .bak"
fi

cat > "$CFG_PATH" <<EOF
[Interface]
PrivateKey = ${SERVER_PRIV}
Address = ${WG_ADDRESS}
ListenPort = ${WG_PORT}
SaveConfig = false

# Добавляйте пиров через wg_peer_add.sh
EOF

chmod 600 "$CFG_PATH"
log "Базовый конфиг создан: ${CFG_PATH}"
log "Server public key: ${SERVER_PUB}"
log "Дальше: добавьте peers, затем: wg-quick up ${WG_IFACE}"
