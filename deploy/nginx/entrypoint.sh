#!/usr/bin/env bash
set -euo pipefail

: "${SERVER_NAME:?SERVER_NAME is required}"
: "${EMAIL:?EMAIL is required}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8000}"

CERT_DIR="/etc/letsencrypt/live/${SERVER_NAME}"

echo "[ENTRYPOINT] Rendering nginx config for ${SERVER_NAME}, upstream app:${UPSTREAM_PORT}"
envsubst '${SERVER_NAME} ${UPSTREAM_PORT}' < /etc/nginx/conf.d/vpppn.conf.template > /etc/nginx/conf.d/default.conf

mkdir -p /var/www/certbot
nginx -t

if [[ -d "/etc/letsencrypt/live" ]]; then
  for d in /etc/letsencrypt/live/*; do
    if [[ -d "$d" && "$(basename "$d")" != "${SERVER_NAME}" ]]; then
      echo "[ENTRYPOINT] Removing legacy cert for $(basename "$d") (current domain: ${SERVER_NAME})"
      rm -rf "/etc/letsencrypt/live/$(basename "$d")" \
             "/etc/letsencrypt/archive/$(basename "$d")" \
             "/etc/letsencrypt/renewal/$(basename "$d").conf" || true
    fi
  done
fi

if [[ ! -f "${CERT_DIR}/fullchain.pem" ]]; then
  echo "[ENTRYPOINT] No existing certs for ${SERVER_NAME}, requesting..."
  echo "[ENTRYPOINT] Starting temporary nginx for ACME challenge..."
  nginx
  certbot certonly --webroot -w /var/www/certbot -d "${SERVER_NAME}" --email "${EMAIL}" --agree-tos --non-interactive || {
    echo "[ENTRYPOINT] Initial cert issuance failed"; exit 1;
  }
  echo "[ENTRYPOINT] Stopping temporary nginx after issuance..."
  nginx -s stop || true
else
  echo "[ENTRYPOINT] Existing certs found for ${SERVER_NAME}, skipping issuance."
fi

renew_loop() {
  while true; do
    sleep 12h
    certbot renew --webroot -w /var/www/certbot --quiet && nginx -s reload
  done
}

renew_loop &

echo "[ENTRYPOINT] Starting nginx..."
nginx -g "daemon off;"
