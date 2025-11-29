# VPN bot / WireGuard control skeleton

Базовый каркас на Python (aiogram 3 + SQLAlchemy + Postgres) для управления временными VPN-ключами через Telegram-бота.

## Стек
- Python 3.11, aiogram 3.x
- SQLAlchemy 2.x + asyncpg
- Postgres 15 (по умолчанию) — можно переключить на SQLite
- Docker / docker-compose

## Запуск
1. Создай `.env` на основе `.env.example` и укажи `BOT_TOKEN` и `ADMIN_IDS` (через запятую).  
2. `make up` (или `docker compose up --build`).  
3. Бот поднимется и создаст таблицы автоматически. Команда запуска: `python -m app.main`.

## Что умеет бот
- /start с инлайн-меню.
- Создание временных ключей с выбором TTL (12/24/72 ч) и лимитом устройств (`MAX_KEYS_PER_USER`).
- Список ключей с отметками активен/истёк + инлайн-отзыв активных.
- Админ-панель (фильтрация активные / просроченные / все), доступ только для `ADMIN_IDS`.

## Структура
- `app/config.py` — конфиг из env.
- `app/db.py` — подключение и создание таблиц.
- `app/models.py` — модели User, VpnKey.
- `app/services.py` — бизнес-логика (лимиты, создание, отзыв).
- `app/bot/...` — роутеры aiogram, клавиатуры, фильтры.
- `docker-compose.yml` — сервисы `app` и `db`.

## Дальше
- Подключить генерацию/выдачу реальных WireGuard-конфигов вместо заглушки.
- Добавить биллинг/оплаты, ротацию ключей, алерты в бот.
- При необходимости заменить Postgres на SQLite (обновить `DATABASE_URL`).
