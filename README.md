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
   - `INITIAL_BALANCE` и `BILLING_COST_PER_KEY` регулируют кредитную модель.
2. `make up` (или `docker compose up --build`).  
3. При старте `alembic upgrade head` прогонит миграции, после этого запустится бот.

## Что умеет бот
- /start с инлайн-меню; доступ в админ-панель только для `ADMIN_IDS`.
- Создание временных ключей с выбором TTL (12/24/72 ч) и лимитом устройств (`MAX_KEYS_PER_USER`); сразу отдаётся реальный WireGuard-конфиг и приватный ключ (не сохраняется!).
- Лимит устройств. Биллинг по умолчанию выключен (`BILLING_ENABLED=false`); можно включить кредиты (`BILLING_COST_PER_KEY`, `INITIAL_BALANCE`).
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
- `docker-compose.yml` — сервисы `app` и `db`.

## Дальше
- Подключить управление реальным WireGuard-интерфейсом/пирами (добавление/удаление на сервере) и метрики.
- Интегрировать реальные платежные шлюзы и уведомления (почта/Slack/Telegram) для алертов.
- При необходимости заменить Postgres на SQLite (обновить `DATABASE_URL`).
