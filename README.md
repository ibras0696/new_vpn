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
- Сервер/локальная машина с интернетом и доступом к Telegram, Docker Hub и GitHub.
- Python ≥ 3.11, Git, Make, Docker + Docker Compose.
- Токен Telegram-бота, ID администратора.
- XRay Core установлен на том сервере, где будут применяться конфиги.

## Быстрый bootstrap-скрипт
Для «чистого» Ubuntu 22.04/24.04 есть готовый сценарий, который делает большинство рутинных шагов:

```bash
curl -fsSL https://raw.githubusercontent.com/ibras0696/new_vpn/main/scripts/bootstrap.sh \
  | sudo APP_DIR=/opt/new_vpn bash
```

Скрипт:
1. Проверяет зависимости, ставит пакеты (curl, git, make, python3, ufw и т.д.).
2. Устанавливает Docker CE + compose plugin (если их ещё нет).
3. При необходимости создаёт пользователя (`APP_USER=name`).
4. Скачивает XRay Core указанной версии (`XRAY_VERSION`, по умолчанию 25.10.15) и настраивает systemd unit.
5. Клонирует репозиторий в `APP_DIR` (по умолчанию `/opt/new_vpn`).

Можно также запускать скрипт уже внутри репозитория: `sudo bash scripts/bootstrap.sh` — он не будет повторно клонировать проект, если `.git` уже существует.

Переменные окружения, которые можно переопределить: `APP_DIR`, `REPO_URL`, `APP_USER`, `UFW_PORTS="443 10085"`, `XRAY_VERSION`.

После выполнения bootstrap дальше действуй по шагам из раздела «Развёртывание вручную»: заполни `.env`, подними контейнер, скопируй сгенерированный `config.json` в `/etc/xray/`, перезапусти XRay и проверь доступ к API.

## Локальный запуск (без Docker)
1. Клонируй репозиторий `git clone https://github.com/ibras0696/new_vpn.git` и перейди в каталог.
2. Создай виртуальное окружение: `python3 -m venv .venv && source .venv/bin/activate`.
3. Установи зависимости: `make dev-install`.
4. Скопируй конфиг: `cp .env.example .env`. Для локальной отладки достаточно заполнить `BOT_TOKEN`, `ADMIN_ID`. Если нет XRay, выставь `XRAY_API_ENABLED=false`.
5. Запусти бота: `make run`.

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
| `XRAY_API_LISTEN` | Адрес, на котором XRay слушает API (`0.0.0.0` для доступа из Docker) |
| `XRAY_API_HOST` | Куда подключается бот (обычно внешний IP сервера; локально — `host.docker.internal`) |
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

## Развёртывание на сервере (ручной сценарий)

### Этап 0. Проверка связи
```bash
ping -c 3 8.8.8.8
nslookup registry-1.docker.io
curl https://api.telegram.org
```
Все команды должны выполняться без ошибок. Если нет — настрой DNS/маршруты (например, пропиши `DNS=1.1.1.1 8.8.8.8` в `/etc/systemd/resolved.conf`, перезапусти `systemd-resolved`, проверь `sudo ufw status verbose`).

### Этап 1. Подготовка сервера
Если bootstrap-скрипт не запускал, сделай то же вручную:
1. **Клонируй репозиторий, чтобы получить скрипты.**
   ```bash
   git clone https://github.com/ibras0696/new_vpn.git
   cd new_vpn
   ```
2. **Установи пакеты и Docker.**
   ```bash
   sudo python3 scripts/setup_ubuntu.py --admin <user> --ports 443 10085
   ```
   (или вручную поставь git/make/docker/ufw и открой нужные порты). После выполнения перезайди в систему, чтобы применились группы docker/sudo.
3. **Установи XRay и systemd unit:**
   ```bash
   sudo bash -c 'mkdir -p /etc/xray /var/log/xray'
   sudo bash -c 'curl -L https://github.com/XTLS/Xray-core/releases/download/v25.10.15/Xray-linux-64.zip -o /tmp/xray.zip'
   sudo bash -c 'apt install -y unzip && unzip /tmp/xray.zip -d /usr/local/share/xray'
   sudo bash -c 'install -m 755 /usr/local/share/xray/xray /usr/local/bin/xray'
   sudo python3 scripts/install_xray_service.py --exec /usr/local/bin/xray --config /etc/xray/config.json
   ```
   Теперь `sudo systemctl status xray` должен показывать активный сервис.

### Этап 2. Подготовка проекта и `.env`
Если ты ещё не в каталоге проекта (например, только что выполнил bootstrap и уже находишься в `/opt/new_vpn`, пропусти следующие две команды):
```bash
git clone https://github.com/ibras0696/new_vpn.git
cd new_vpn
```
Далее подготовь рабочие файлы:
```bash
cp .env.example .env
mkdir -p etc/xray   # каталог для конфигов внутри репозитория
```
В `.env` обязательно укажи:
- `BOT_TOKEN`, `ADMIN_ID`
- `XRAY_DOMAIN` и `XRAY_API_HOST` = внешний IP или домен
- `XRAY_API_LISTEN=0.0.0.0`
- при необходимости скорректируй путь `XRAY_CONFIG_PATH` (по умолчанию `./etc/xray/config.json`).

### Этап 3. Запуск контейнера и генерация конфига
```bash
docker compose up -d --build
```
После старта в каталоге появится файл, на который указывает `XRAY_CONFIG_PATH` (стандартно `./etc/xray/config.json`).

### Этап 4. Применение конфига XRay
```bash
# если используешь путь по умолчанию
sudo cp ./etc/xray/config.json /etc/xray/config.json

# если менял XRAY_CONFIG_PATH, скопируй файл из указанного пути
# sudo cp <путь из XRAY_CONFIG_PATH> /etc/xray/config.json

sudo systemctl restart xray
sudo ss -ltnp | grep 10085   # ожидаем 0.0.0.0:10085 или *:10085
```
Если порт слушается только на `127.0.0.1`, вернись к Этапу 2 и убедись, что `XRAY_API_LISTEN=0.0.0.0`.

### Этап 5. Проверка API из контейнера
```bash
docker compose exec bot python - <<'PY'
import socket
socket.create_connection(('YOUR_SERVER_IP', 10085), timeout=3)
print('OK: API доступен')
PY
```
Замените `YOUR_SERVER_IP` на IP/домен сервера. Сообщение `OK` означает, что бот сможет управлять XRay. При `Connection refused` проверь firewall и настройки XRay.

### Этап 6. Убедись, что запущен один бот
- `docker compose ps` — должен быть один контейнер `bot`.
- Если ранее запускал бота вручную (`python -m main`), останови процесс (`pkill -f "python -m main"`). Иначе Telegram отдаст `Conflict: terminated by other getUpdates request`.

### Этап 7. Финальные проверки
- `docker compose logs -f bot` — нет ли `TelegramNetworkError`.
- Создай тестовый ключ/удали ключ через меню. Если в логах появится `failed to dial ...`, вернись к Этапу 5.

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
