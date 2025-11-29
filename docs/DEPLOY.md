# Развёртывание и настройка (пошагово)

Этот файл для «чайников»: минимальные действия, чтобы запустить бота, TLS-прокси и базовую настройку WireGuard на сервере.

## 1) Подготовка окружения
1. Установи Docker и docker-compose plugin (на чистом сервере можно: `sudo bash scripts/bootstrap_server.sh`).
2. Клонируй репозиторий на сервер.
3. Скопируй `.env.example` → `.env` и заполни:
   - `BOT_TOKEN` — токен Telegram бота (BotFather).
   - `ADMIN_IDS` — id админов (через запятую).
   - `WG_ENDPOINT`, `WG_SERVER_PUBLIC_KEY`, `WG_CLIENT_ADDRESS_CIDR` и т.п. — под твою сеть.
4. Если используешь nginx+certbot в Docker: скопируй `.env.nginx.example` → `.env.nginx`, впиши домен (`SERVER_NAME`), почту (`EMAIL`) и порт приложения (`UPSTREAM_PORT`, по умолчанию 8000).

## 2) Запуск приложения (без TLS-прокси)
```
make up
```
или `docker compose up --build`.  
Миграции применяются автоматически, бот стартует. Проверка логов: `make app-logs`.

## 3) Запуск с nginx+certbot в Docker (в общем compose)
1. Убедись, что DNS-домен `SERVER_NAME` указывает на сервер (A/AAAA запись).
2. В `.env` заполни `SERVER_NAME`, `EMAIL`, `UPSTREAM_PORT` (если нужен не 8000).
3. Запусти стек:
```
docker compose up -d --build
```
   - БД стартует первой; у сервиса app есть depends_on с healthcheck БД, nginx ждёт app по depends_on.
4. Что делает контейнер `nginx`:
   - Рендерит конфиг из `deploy/nginx/conf.d/vpppn.conf.template`.
   - Если сертификат для `SERVER_NAME` не найден, запрашивает его через webroot (папка `/var/www/certbot` смонтирована на `./data/certbot/www`). Для запроса поднимается временный nginx, затем основной перезапускается.
   - Раз в 12 часов выполняет `certbot renew` и `nginx -s reload`.
   - При смене домена (`SERVER_NAME`) удаляет старые каталоги Let’s Encrypt и запрашивает новый сертификат.
   - Если поставить `DISABLE_CERTBOT=true`, nginx стартует без TLS (HTTP), certbot не вызывается — удобно для тестов по IP.
5. Логи nginx/certbot: `docker compose logs -f nginx`.

Полезные каталоги (монтируются из хоста):
- `./data/letsencrypt` → `/etc/letsencrypt` (серты и метаданные).
- `./data/certbot/www` → `/var/www/certbot` (webroot для проверки).

## 4) Базовая настройка WireGuard на сервере (опционально, без Docker)
1. Сгенерировать серверные ключи и черновик `wg0.conf`:
```
sudo WG_IFACE=wg0 WG_PORT=51820 WG_ADDRESS=10.8.0.1/24 bash scripts/wg_server_init.sh
```
   - Ключи лягут в `/etc/wireguard/server_private.key`, `server_public.key`, конфиг в `/etc/wireguard/wg0.conf`.
2. Поднять интерфейс:
```
sudo wg-quick up wg0
```
3. Добавить пира (пример):
```
sudo WG_IFACE=wg0 bash scripts/wg_peer_add.sh PUBLIC_KEY "10.8.0.2/32" PRESHARED_KEY
```
   - Скрипт допишет блок [Peer] в `/etc/wireguard/wg0.conf` и применит `wg syncconf`.
4. Проверка:
```
sudo wg show
```

## 5) Ручная установка nginx+certbot на хосте (без Docker, опционально)
Если нужен системный nginx:
```
sudo DOMAIN=example.com EMAIL=you@example.com UPSTREAM_PORT=8000 bash scripts/nginx_certbot_setup.sh
```
Скрипт поставит nginx+certbot, создаст конфиг, выпустит сертификат и добавит post-hook для `systemctl reload nginx`.

## 6) Частые действия
- Перезапуск приложения после смены `.env`: `docker compose up -d --force-recreate app` (или `make compose-recreate`).
- Проверка статуса: `docker compose ps`, логи: `make app-logs`, `docker compose -f docker-compose.nginx.yml logs -f nginx`.
- Очистка старых сертификатов при смене домена в Docker — выполняется автоматически entrypoint’ом nginx-контейнера.
