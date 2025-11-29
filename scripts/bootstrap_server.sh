#!/usr/bin/env bash
# Минимальный bootstrap сервера: ставит Docker + docker compose plugin и wireguard-tools.
# Запускается с правами root (или через sudo). Не перезаписывает существующие конфиги.
set -euo pipefail

log() { printf '[BOOTSTRAP] %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  log "Запустите от root (sudo)"; exit 1;
fi

log "Обновление пакетов..."
apt-get update -y

log "Установка Docker + compose plugin..."
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

log "Установка wireguard-tools..."
apt-get install -y wireguard-tools

log "Готово. Проверьте: docker --version; wg --version"
