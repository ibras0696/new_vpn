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
- **Рабочая сеть.** Перед любыми шагами на сервере убедись, что есть интернет:
  ```bash
  ping -c 3 8.8.8.8
  nslookup registry-1.docker.io
  curl https://api.telegram.org
  ```
  Если что-то падает — сначала почини DNS/маршруты (например, пропиши `DNS=1.1.1.1 8.8.8.8` в `/etc/systemd/resolved.conf` и перезапусти `systemd-resolved`).
- **Инструменты:** Python 3.11+, Git, Make, Docker Compose, токен Telegram-бота.
- **XRay Core:** установленный бинарь `xray`, который сможет читать конфиг `/etc/xray/config.json` и принимать API-запросы.
- **База данных:** SQLite (по умолчанию) или PostgreSQL.

## Локальный запуск (без Docker)
1. `git clone https://github.com/ibras0696/new_vpn.git` и переход в каталог проекта.
2. `python3 -m venv .venv && source .venv/bin/activate`.
3. `make dev-install` — установит зависимости.
4. `cp .env.example .env` и укажи минимум `BOT_TOKEN`, `ADMIN_ID`. Для локального режима можно поставить `XRAY_API_ENABLED=false`.
5. `make run` — бот стартует и будет ждать команды.

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
| `XRAY_API_LISTEN` | Где слушает XRay API (`127.0.0.1` или `0.0.0.0`, если доступ из контейнера) |
| `XRAY_API_HOST` | Хост API. Для Docker на Linux добавь `extra_hosts: host.docker.internal:host-gateway` и ставь `host.docker.internal` |
| `XRAY_API_PORT` | Порт API (по умолчанию `10085`) |
| `XRAY_INBOUND_TAG` | Тег inbound-а в XRay |

## Docker
```bash
make docker-build   # сборка образа
docker compose up -d
docker compose logs -f bot
```
В образ включается XRay CLI (`ARG XRAY_VERSION` по умолчанию `25.10.15`). Можно переопределить версию: `docker compose build --build-arg XRAY_VERSION=...`.

> **Примечание (Linux):** docker-compose уже содержит `extra_hosts: host.docker.internal:host-gateway`, поэтому контейнер может обратиться к API XRay на хосте. Укажи `XRAY_API_HOST=host.docker.internal` и, если XRay запущен на этом же сервере, выстави `XRAY_API_LISTEN=0.0.0.0`, чтобы API принимал соединения извне.

## Автоконфигурация сервера (Ubuntu 22.04/24.04)
### scripts/setup_ubuntu.py
Готовит «чистый» сервер: ставит базовые пакеты, Docker, включает UFW, создаёт пользователя.

Полезные флаги:
- `--admin` — имя создаваемого пользователя (если не указать, пользователь не создаётся).
- `--ports` — список портов для UFW (по умолчанию `443 10085` + `OpenSSH`).
- `--skip-docker` — пропустить установку Docker.
- `--dry-run` — только показать команды, ничего не изменяя.

### scripts/install_xray_service.py
Создаёт systemd unit для XRay и запускает сервис.

Параметры:
- `--user` — пользователь systemd (по умолчанию `root`).
- `--unit-path` — путь к unit (по умолчанию `/etc/systemd/system/xray.service`).
- `--log-dir` — каталог логов (создаётся автоматически).
- `--dry-run` — показать содержимое unit без записи.

После генерации юнита проверь статус:
```bash
sudo systemctl status xray
```

## Деплой на сервере (подробно)

### 1. Подготовь окружение
- Убедись, что есть интернет (см. раздел «Требования»). Любые ошибки DNS/маршрута исправь до следующих шагов.
- Запусти скрипт настройки или поставь пакеты вручную:
  ```bash
  sudo python3 scripts/setup_ubuntu.py --admin <user> --ports 443 10085
  ```
  Скрипт создаст пользователя, установит git/make/docker/ufw. Перелогинься, чтобы применились группы.

### 2. Клонируй проект и подготовь `.env`
- Склонируй репозиторий в любую удобную папку.
- `cp .env.example .env` и заполни переменные. Для продакшена обязательно:
  - `XRAY_DOMAIN` — внешний IP или домен.
  - `XRAY_API_HOST` — тот же IP/домен (адрес, куда будет подключаться бот).
  - `XRAY_API_LISTEN=0.0.0.0` — XRay будет слушать API на всех интерфейсах.
  - Остальное под свою инфраструктуру (порт, TLS, БД).

### 3. Собери и запусти контейнер
```bash
docker compose up -d --build
```
В каталоге появится `./etc/xray/config.json` — это свежий конфиг XRay.

### 4. Применяй конфиг XRay
```bash
sudo cp ./etc/xray/config.json /etc/xray/config.json
sudo systemctl restart xray
sudo ss -ltnp | grep 10085    # ожидание: 0.0.0.0:10085 (или *:10085)
```
Если видишь `127.0.0.1:10085`, значит `XRAY_API_LISTEN` не поменяли — вернись к шагу 2.

### 5. Проверь доступ к API из контейнера
```bash
docker compose exec bot python - <<'PY'
import socket
socket.create_connection(('YOUR_SERVER_IP', 10085), timeout=3)
print('OK: API доступен')
PY
```
Если получаешь `OK`, можно работать. При `Connection refused` убедись, что XRay слушает на 0.0.0.0 и firewall открыт.

### 6. Проследи, чтобы бот был один
- `docker compose ps` — должен быть один контейнер `bot`.
- Если есть локальные запуски (`python -m main`), заверши их (`pkill -f "python -m main"`). Иначе Telegram вернёт `Conflict: terminated by other getUpdates request`.

### 7. Контрольные проверки
- `docker compose logs -f bot` — убедись, что нет `TelegramNetworkError`.
- Попробуй создать ключ через меню бота: в логах будет `Команда … завершилась ошибкой` только если API снова недоступен.

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
