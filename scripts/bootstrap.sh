#!/usr/bin/env bash
#
# Быстрый bootstrap-чеклист для сервера под new_vpn:
#  - устанавливает системные пакеты (curl, git, make, python3, ufw и т.д.)
#  - ставит Docker CE и плагин compose
#  - открывает в UFW необходимые порты (443 и 10085 по умолчанию)
#  - при необходимости создаёт системного пользователя
#  - ставит XRay (если ещё не установлен) и настраивает systemd unit
#  - клонирует репозиторий и при желании меняет владельца каталога
#
# Пример запуска:
#   sudo APP_USER=vpnadmin APP_DIR=/opt/new_vpn bash scripts/bootstrap.sh
#
# Переменные окружения:
#   APP_DIR        — куда клонировать репозиторий (по умолчанию /opt/new_vpn)
#   REPO_URL       — какой git-URL использовать
#   APP_USER       — пользователь-владелец каталога проекта (опционально)
#   UFW_PORTS      — список портов для открытия в UFW (по умолчанию "443 10085")
#   XRAY_VERSION   — версия XRay Core для установки (по умолчанию 25.10.15)

set -euo pipefail

APP_DIR=${APP_DIR:-/opt/new_vpn}
REPO_URL=${REPO_URL:-https://github.com/ibras0696/new_vpn.git}
APP_USER=${APP_USER:-}
UFW_PORTS=${UFW_PORTS:-443 10085}
XRAY_VERSION=${XRAY_VERSION:-25.10.15}

log() {
  echo -e "\n==> $1"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Эту команду нужно запускать от root (используй sudo)." >&2
    exit 1
  fi
}

install_packages() {
  log "Устанавливаю системные пакеты"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y \
    curl git make unzip ufw ca-certificates gnupg lsb-release \
    python3 python3-venv python3-pip
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker уже установлен — пропускаю"
    return
  fi

  log "Добавляю Docker репозиторий"
  install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  fi
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list >/dev/null

  log "Ставлю Docker и плагин compose"
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

configure_ufw() {
  log "Настраиваю UFW"
  ufw allow OpenSSH
  for port in ${UFW_PORTS}; do
    ufw allow "${port}/tcp"
  done
  ufw --force enable
  ufw status verbose
}

create_user_if_needed() {
  if [[ -z "${APP_USER}" ]]; then
    return
  fi
  if id "${APP_USER}" >/dev/null 2>&1; then
    log "Пользователь ${APP_USER} уже существует — пропускаю создание"
  else
    log "Создаю пользователя ${APP_USER}"
    useradd -m -s /bin/bash "${APP_USER}"
  fi
  usermod -aG sudo "${APP_USER}"
  usermod -aG docker "${APP_USER}"
}

install_xray_binary() {
  if command -v xray >/dev/null 2>&1; then
    log "XRay уже установлен — пропускаю"
    return
  fi
  log "Ставлю XRay Core v${XRAY_VERSION}"
  TMP_DIR=$(mktemp -d)
  curl -fsSL "https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-64.zip" -o "${TMP_DIR}/xray.zip"
  unzip -q "${TMP_DIR}/xray.zip" -d "${TMP_DIR}"
  install -m 755 "${TMP_DIR}/xray" /usr/local/bin/xray
  if ls "${TMP_DIR}"/*.dat >/dev/null 2>&1; then
    install -m 644 "${TMP_DIR}"/*.dat /usr/local/share/
  fi
  rm -rf "${TMP_DIR}"
}

ensure_repo() {
  log "Клонирую репозиторий"
  if [[ -d "${APP_DIR}/.git" ]]; then
    git -C "${APP_DIR}" pull --ff-only
  else
    rm -rf "${APP_DIR}"
    git clone "${REPO_URL}" "${APP_DIR}"
  fi
  if [[ -n "${APP_USER}" ]]; then
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
  fi
}

install_xray_service() {
  log "Настраиваю systemd unit для XRay"
  python3 "${APP_DIR}/scripts/install_xray_service.py" \
    --exec /usr/local/bin/xray \
    --config /etc/xray/config.json
}

print_next_steps() {
  cat <<EOF

Готово! Что дальше:
  1. Заполни файл .env (см. README).
  2. Запусти контейнер: cd ${APP_DIR} && docker compose up -d --build.
  3. Скопируй сгенерированный конфиг (XRAY_CONFIG_PATH) в /etc/xray/config.json и перезапусти XRay.
  4. Проверь доступ к API из контейнера:
       docker compose exec -T bot python - <<'PY'
       import socket
       socket.create_connection(('host.docker.internal', 10085), timeout=3)
       print('OK')
       PY

Подробнее см. раздел "Развёртывание" в README.
EOF
}

main() {
  require_root
  install_packages
  install_docker
  create_user_if_needed
  configure_ufw
  install_xray_binary
  ensure_repo
  install_xray_service
  print_next_steps
}

main "$@"
