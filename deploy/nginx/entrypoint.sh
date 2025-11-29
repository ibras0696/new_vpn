#!/usr/bin/env bash
set -euo pipefail

: "${SERVER_NAME:?SERVER_NAME is required}"
: "${EMAIL:?EMAIL is required}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8000}"
DISABLE_CERTBOT="${DISABLE_CERTBOT:-false}"

if [[ "${DISABLE_CERTBOT,,}" == "true" ]]; then
  echo "[ENTRYPOINT] DISABLE_CERTBOT=true — запускаю nginx без TLS (HTTP, без сертификата)."
  cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://app:${UPSTREAM_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
else
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
fi

renew_loop() {
  while true; do
    sleep 12h
    certbot renew --webroot -w /var/www/certbot --quiet && nginx -s reload
  done
}

if [[ "${DISABLE_CERTBOT,,}" != "true" ]]; then
  renew_loop &
fi

echo "[ENTRYPOINT] Starting nginx..."
nginx -g "daemon off;"
