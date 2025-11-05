# new_vpn — Telegram‑бот для управления VLESS ключами

Бот помогает администратору выдавать, просматривать и отзывать VLESS‑ключи для XRay. Ключи публикуются в Telegram одним нажатием с QR‑кодом, а состояние XRay синхронизируется через API.

## Возможности
- инлайн‑меню для создания ключей с пресетами и произвольным сроком;
- список всех ключей, удаление с подтверждением;
- автоматическая регистрация/удаление клиентов в XRay API;
- планировщик очистки просроченных ключей;
- скрипты настройки Ubuntu и установки systemd‑юнита XRay;
- Makefile с типовыми задачами разработки и деплоя.

## Структура проекта
```
handlers/          # Telegram-хендлеры, клавиатуры и FSM
services/          # Интеграция с XRay, планировщик, клиенты
data/              # async SQLAlchemy: модели, репозитории, слой БД
filters/           # Кастомные фильтры aiogram (админ и т.п.)
scripts/           # Автоматизация подготовки сервера и XRay
tests/             # PyTest (XRay API негативные сценарии)
Dockerfile         # Образ бота с XRay CLI
docker-compose.yml # Сервис "bot" (переменные берёт из .env)
Makefile           # Частые команды: установка, запуск, Docker, тесты
pyproject.toml     # PEP 621 + Setuptools
```

## Требования
- Python 3.11+
- Git, Make (`sudo apt-get install -y git make` на Ubuntu, если скрипт ещё не ставил)
- Telegram Bot API токен
- XRay Core (CLI `xray`, API включённый inbound)
- SQLite (по умолчанию) или PostgreSQL

## Установка и запуск (локально)
```bash
git clone https://github.com/<your-account>/new_vpn.git
cd new_vpn
python3 -m venv .venv
source .venv/bin/activate
make dev-install               # установка зависимостей
cp .env.example .env           # скопируй и заполни обязательные переменные
make run                       # запуск бота
```

> Для запуска без XRay API выставь `XRAY_API_ENABLED=false` — бот пропустит интеграционные вызовы.

## Makefile: основные команды
| Команда | Описание |
|---------|----------|
| `make help` | показать список целей |
| `make install` / `make dev-install` | установка зависимостей (`dev` включает pytest и ruff) |
| `make run` | запустить бота локально |
| `make lint` / `make format` | проверка и автоформат Ruff |
| `make test` | запустить PyTest |
| `make docker-build` | собрать Docker-образ |
| `make compose-up` / `make compose-down` | поднять/остановить сервис через docker-compose |
| `make docker-logs` | tail логов compose |
| `make clean` | очистить кеши и артефакты |

## Конфигурация `.env`
| Переменная | Значение |
|-----------|----------|
| `BOT_TOKEN` | Токен Telegram-бота |
| `ADMIN_ID` | Telegram ID администратора |
| `DB_ENGINE` | `sqlite+aiosqlite` или `postgresql+asyncpg` |
| `DB_NAME` | Путь/имя базы |
| `XRAY_DOMAIN` | Домен или IP сервера |
| `XRAY_PORT` | Порт VLESS входа |
| `XRAY_SECURITY` | `tls` или `none` |
| `XRAY_NETWORK` | `tcp`, `ws`, `grpc` |
| `XRAY_API_ENABLED` | `true` / `false` |
| `XRAY_API_HOST` | Хост API (для Docker укажи `host.docker.internal` или IP хоста) |
| `XRAY_API_PORT` | Порт API (по умолчанию `10085`) |
| `XRAY_INBOUND_TAG` | Тег inbound-а в XRay |

## Docker
```bash
make docker-build   # сборка образа
docker compose up -d
docker compose logs -f bot
```
В образ включается XRay CLI (`ARG XRAY_VERSION` по умолчанию `25.10.15`). Можно переопределить версию: `docker compose build --build-arg XRAY_VERSION=...`.

## Автоконфигурация сервера (Ubuntu 22.04/24.04)
### scripts/setup_ubuntu.py
Готовит «чистый» сервер: ставит базовые пакеты, Docker, включает UFW, создаёт пользователя.
```bash
sudo python3 scripts/setup_ubuntu.py --admin vpppn --ports 443 10085
```
Полезные флаги:
- `--admin` — имя создаваемого пользователя (если не указать, пользователь не создаётся).
- `--ports` — список портов для UFW (по умолчанию `443 10085` + `OpenSSH`).
- `--skip-docker` — пропустить установку Docker.
- `--dry-run` — только показать команды, ничего не изменяя.

### scripts/install_xray_service.py
Создаёт systemd unit для XRay и запускает сервис.
```bash
sudo python3 scripts/install_xray_service.py \
  --user root \
  --exec /usr/local/bin/xray \
  --config /etc/xray/config.json
```
Параметры:
- `--user` — пользователь systemd (по умолчанию `root`).
- `--unit-path` — путь к unit (по умолчанию `/etc/systemd/system/xray.service`).
- `--log-dir` — каталог логов (создаётся автоматически).
- `--dry-run` — показать содержимое unit без записи.

После генерации юнита проверь статус:
```bash
sudo systemctl status xray
```

## Деплой на сервере (коротко)
1. Подготовь сервер: используй `scripts/setup_ubuntu.py` или установи вручную `git`, `make`, Docker, UFW.
2. Клонируй репозиторий в удобный каталог и назначь владельца (если работаешь не от root).
3. Создай и заполни `.env`.
4. Собери и запусти контейнер `docker compose up -d --build` (или `make compose-up`).
5. После генерации `/etc/xray/config.json` перезапусти XRay: `sudo systemctl restart xray`.

## Тестирование
```bash
make test
```
PyTest проверяет обработку ошибок при работе с XRay CLI.

## Отладка
- Если XRay API временно недоступен, поставь `XRAY_API_ENABLED=false` — бот продолжит работу и отложит синхронизацию.
- Логи XRay: `journalctl -u xray -f`.
- Логи бота в Docker: `docker compose logs -f bot`.

## Лицензия
Проект распространяется на условиях MIT. Contributions welcome!
