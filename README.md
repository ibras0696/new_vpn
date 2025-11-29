# VPN bot / WireGuard control skeleton

Бот/бэкенд на Python (aiogram 3 + SQLAlchemy + Postgres) для управления временными WireGuard-ключами через Telegram.

## Стек
- Python 3.11, aiogram 3.x
- SQLAlchemy 2.x + asyncpg
- Alembic (миграции)
- Postgres 15 (по умолчанию) — можно переключить на SQLite при необходимости
- wireguard-tools (генерация ключей внутри контейнера)
- Docker / docker-compose

## Запуск
1. Создай `.env` на основе `.env.example` и укажи `BOT_TOKEN` и `ADMIN_IDS` (через запятую).  
   - Обязательно задай `WG_ENDPOINT`, `WG_SERVER_PUBLIC_KEY`, при необходимости `WG_ALLOWED_IPS`, `WG_DNS`, `WG_CLIENT_ADDRESS_CIDR`.  
   - Биллинг отключён (`BILLING_ENABLED=false`, `BILLING_COST_PER_KEY=0`), лимит устройств (`MAX_KEYS_PER_USER`) действует только для обычных пользователей; админы без лимитов.
2. `make up` (или `docker compose up --build`).  
3. При старте `alembic upgrade head` прогонит миграции, после этого запустится бот.

## Что умеет бот
- /start с инлайн-меню; доступ в админ-панель только для `ADMIN_IDS`.
- Создание ключей с выбором TTL: 1 день, 1 неделя, 30/90 дней, Безлимит (~10 лет). Лимит устройств (`MAX_KEYS_PER_USER`) для обычных пользователей; админы без ограничений. Сразу отдаётся реальный WireGuard-конфиг, приватный ключ не хранится.
- Список ключей с отметками активен/истёк, адресом; кнопки для отзыва и ротации (новый конфиг, старый ключ отзывается).
- Админ-панель: фильтрация активные/просроченные/все и просмотр последних алертов.
- Фоновая зачистка просроченных ключей (`CLEANUP_INTERVAL_MINUTES`), события фиксируются как алерты.

## Структура
- `app/config.py` — конфиг из env.
- `app/db.py` — подключение к БД.
- `app/models.py` — модели User, VpnKey, BillingEvent, Alert.
- `app/services.py` — бизнес-логика (лимиты, биллинг, ротация, алерты, WireGuard-конфиг).
- `app/wireguard.py` — генерация ключей и конфигов.
- `app/migrations_runner.py`, `alembic/` — миграции.
- `app/bot/...` — роутеры aiogram, клавиатуры, фильтры.
- `docker-compose.yml` — сервисы `app`, `db`, `nginx` (TLS через certbot, авто-renew, прокси на app).
- `scripts/` — служебные скрипты:
  - `scripts/bootstrap_server.sh` — установка Docker/compose и wireguard-tools на сервер.
  - `scripts/wg_server_init.sh` — генерация серверных ключей и чернового `/etc/wireguard/wg0.conf`.
  - `scripts/wg_peer_add.sh` — добавление пиров в конфиг и применение через `wg syncconf`.
  - `scripts/nginx_certbot_setup.sh` — установка Nginx+Certbot, выпуск TLS-серта и post-hook для авто-релоада.
- `deploy/` — примеры конфигов:
  - `deploy/nginx/vpppn.conf.example` — шаблон nginx с прокси и TLS.
  - `deploy/nginx/` — Dockerfile + entrypoint для контейнера nginx+certbot.
- `.env.nginx.example` — переменные для nginx+certbot (домен, email, upstream).

Примечание по сертификатам в Docker: при смене `SERVER_NAME` entrypoint удалит старые каталоги `/etc/letsencrypt/{live,archive,renewal}` для прежних доменов и запросит новый сертификат для актуального.

Подробный гайд по развёртыванию см. в `docs/DEPLOY.md`.

## Дальше
- Подключить управление реальным WireGuard-интерфейсом/пирами (добавление/удаление на сервере) и метрики.
- Интегрировать реальные платежные шлюзы и уведомления (почта/Slack/Telegram) для алертов.
- При необходимости заменить Postgres на SQLite (обновить `DATABASE_URL`).
