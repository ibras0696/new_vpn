#!/usr/bin/env bash
# Устанавливает Nginx + certbot и разворачивает базовый конфиг с TLS.
# Требует: root. Требует, чтобы домен уже указывал на сервер.
set -euo pipefail

DOMAIN="${DOMAIN:-example.com}"
EMAIL="${EMAIL:-admin@example.com}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8000}"
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}.conf"
WEBROOT="/var/www/certbot"

log() { printf '[NGINX-CERTBOT] %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  log "Запустите от root (sudo)"; exit 1;
fi

log "Обновление пакетов..."
apt-get update -y

log "Установка nginx и certbot..."
apt-get install -y nginx certbot python3-certbot-nginx

mkdir -p "$WEBROOT"

log "Создание конфигурации nginx для $DOMAIN ..."
cat > "$NGINX_CONF" <<EOF
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name ${DOMAIN};
    location /.well-known/acme-challenge/ {
        root ${WEBROOT};
    }
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://127.0.0.1:${UPSTREAM_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
    }
}
EOF

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/${DOMAIN}.conf
log "Проверка конфигурации nginx..."
nginx -t
systemctl restart nginx

log "Запрос сертификата для ${DOMAIN}..."
certbot --nginx --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN" --redirect --hsts --staple-ocsp

log "Создание post-hook для авто-релоада nginx после продления..."
HOOK="/etc/letsencrypt/renewal-hooks/post/reload-nginx.sh"
cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
systemctl reload nginx
EOF
chmod +x "$HOOK"

log "Готово. Проверяйте: systemctl status nginx && certbot renew --dry-run"
