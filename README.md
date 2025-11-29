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

## Перед запуском (чеклист)
- DNS: `SERVER_NAME` должен резолвиться на сервер (A/AAAA).  
- Порты: 80/443 (для certbot/nginx) и 51820/UDP (WireGuard) должны быть открыты на фаерволе/облаке.  
- BOT_TOKEN: валиден (иначе aiogram упадёт с `TokenValidationError`).  
- Тома/права: `./data/letsencrypt`, `./data/certbot/www`, `pgdata` доступны для записи.

## Предупреждения и подводные камни
- Certbot не выпустит сертификат, если домен не резолвится или 80/443 закрыты — nginx-контейнер может завершиться; исправьте DNS/фаервол и перезапустите `docker compose up -d --build`.
- Неверный BOT_TOKEN — бот не стартует.
- Изменение `WG_CLIENT_ADDRESS_CIDR` или `WG_ENDPOINT` без пересоздания ключей может вызвать конфликт адресов/невалидные конфиги — перевыдавайте ключи.
- Интерфейс WireGuard не настраивается автоматически: приложение генерирует конфиги, но добавление пиров в системный WG делайте вручную (`scripts/wg_server_init.sh`, `scripts/wg_peer_add.sh`) или допишите автоматизацию.
- TTL «Безлимит» = ~10 лет вперёд, не бесконечность.
- При первом старте Postgres, если тормозит, nginx может дать 502 — `restart` у сервиса app перекроет после запуска БД.
- DeprecationWarning aiogram (parse_mode): можно убрать, поменяв инициализацию бота на `DefaultBotProperties(parse_mode=ParseMode.HTML)` (оставлено в TODO).

## Бэкапы и восстановление
- База: том `pgdata`.
- TLS: `./data/letsencrypt` (серты/метаданные), `./data/certbot/www` (webroot). При смене домена auto-clean в entrypoint удалит старые каталоги, но бэкапить полезно.

## Логирование/мониторинг
- Быстрые логи: `docker compose logs -f app` и `docker compose logs -f nginx`.
- Прометей/алерты не подключены — добавьте при необходимости.

## Скрипты: когда и как запускать
- Bootstrap сервера (Docker + wg): `sudo bash scripts/bootstrap_server.sh` (используй только на чистом сервере).
- Генерация серверного WG-конфига: `sudo WG_IFACE=wg0 WG_PORT=51820 WG_ADDRESS=10.8.0.1/24 bash scripts/wg_server_init.sh`.
- Добавление пира в системный WG: `sudo WG_IFACE=wg0 bash scripts/wg_peer_add.sh PUBLIC_KEY "10.8.0.2/32" PRESHARED_KEY`.
- Системный nginx+certbot (без Docker): `sudo DOMAIN=example.com EMAIL=you@example.com UPSTREAM_PORT=8000 bash scripts/nginx_certbot_setup.sh`.
- Все эти скрипты запускаются вручную, ничего не стартует автоматически.

## Дальше
- Подключить управление реальным WireGuard-интерфейсом/пирами (добавление/удаление на сервере) и метрики.
- Интегрировать реальные платежные шлюзы и уведомления (почта/Slack/Telegram) для алертов.
- При необходимости заменить Postgres на SQLite (обновить `DATABASE_URL`).
