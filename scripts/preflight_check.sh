#!/usr/bin/env bash
# Простая проверка перед запуском: DNS, порты, env.
# Не открывает порты и не меняет конфиги — только проверка и подсказки.
set -euo pipefail

SERVER_NAME="${SERVER_NAME:-${SERVER_NAME:-}}"
BOT_TOKEN="${BOT_TOKEN:-${BOT_TOKEN:-}}"

echo "== Preflight check =="

if [[ -z "$SERVER_NAME" ]]; then
  echo "[WARN] SERVER_NAME не задан (для certbot/nginx)."
else
  echo "[INFO] Проверяю DNS для ${SERVER_NAME}..."
  if getent ahosts "$SERVER_NAME" >/dev/null; then
    ip=$(getent ahosts "$SERVER_NAME" | head -n1 | awk '{print $1}')
    echo "[OK] ${SERVER_NAME} резолвится в ${ip}"
  else
    echo "[ERR] ${SERVER_NAME} не резолвится. Настройте A/AAAA запись."
  fi
fi

if [[ -z "$BOT_TOKEN" || "$BOT_TOKEN" == "please_set_bot_token" ]]; then
  echo "[ERR] BOT_TOKEN не задан или заглушка."
else
  echo "[OK] BOT_TOKEN установлен (валидность не проверяется здесь)."
fi

echo "[INFO] Проверка доступности портов 80/443/51820 (локально)..."
for port in 80 443 51820; do
  if ss -tulwn | grep -q ":${port}"; then
    echo "[WARN] Порт ${port} уже занят локальным процессом."
  else
    echo "[OK] Порт ${port} свободен."
  fi
done

echo "[HINT] Убедитесь, что фаервол/облако разрешают 80/443 (HTTP/HTTPS) и 51820/UDP (WG)."
