Отлично 💪
Вот готовая, доработанная версия твоего README — **v1.1 (Server-Ready Edition)**
Я внёс только нужные правки: никакой воды, всё чисто, структурно и рассчитано на нормальный Linux-сервер.
👇 Можешь просто заменить свой `README.md` этим файлом и закоммитить в `main`.

---

# new_vpn — Telegram-бот для управления VLESS-ключами

Бот помогает администратору выдавать, просматривать и отзывать VLESS-ключи для XRay.
Ключи публикуются в Telegram одним нажатием с QR-кодом, а состояние XRay синхронизируется через API.

---

## ⚙️ Возможности

* Инлайн-меню для создания ключей с пресетами и произвольным сроком.
* Просмотр и удаление ключей с подтверждением.
* Автоматическая регистрация/удаление клиентов в XRay API.
* Планировщик очистки просроченных ключей.
* Скрипты настройки Ubuntu и установки systemd-юнита XRay.
* Makefile с типовыми задачами разработки и деплоя.

---

## 🧩 Структура проекта

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

---

## 🧾 Требования

* Ubuntu 22.04 / 24.04 с интернетом и доступом к Telegram, Docker Hub и GitHub.
* Python ≥ 3.11, Git, Make, Docker + Docker Compose.
* Токен Telegram-бота, ID администратора.
* XRay Core установлен на том же сервере (бот управляет его API).

---

## 🚀 Локальный запуск (без Docker)

```bash
git clone https://github.com/ibras0696/new_vpn.git
cd new_vpn
python3 -m venv .venv && source .venv/bin/activate
make dev-install
cp .env.example .env
```

Минимальные настройки для локального теста:

```
BOT_TOKEN=<твой_токен>
ADMIN_ID=<твой_id>
XRAY_API_ENABLED=false
```

Запуск:

```bash
make run
```

> Если XRay API отсутствует, установи `XRAY_API_ENABLED=false`, чтобы бот пропускал интеграцию.

---

## 🧰 Makefile: основные команды

| Команда                                 | Описание                                     |
| --------------------------------------- | -------------------------------------------- |
| `make help`                             | показать все цели                            |
| `make dev-install`                      | установка зависимостей с тестами и линтингом |
| `make run`                              | локальный запуск                             |
| `make docker-build`                     | сборка Docker-образа                         |
| `make compose-up` / `make compose-down` | запуск / остановка сервиса                   |
| `make docker-logs`                      | просмотр логов контейнера                    |
| `make test`                             | запуск PyTest                                |
| `make clean`                            | очистка кешей                                |

---

## ⚙️ Конфигурация `.env`

| Переменная         | Значение                                                  |
| ------------------ | --------------------------------------------------------- |
| `BOT_TOKEN`        | Токен Telegram-бота                                       |
| `ADMIN_ID`         | Telegram ID администратора                                |
| `DB_ENGINE`        | `sqlite+aiosqlite` или `postgresql+asyncpg`               |
| `DB_NAME`          | Путь/имя базы                                             |
| `XRAY_DOMAIN`      | Домен или IP сервера                                      |
| `XRAY_PORT`        | Порт VLESS входа                                          |
| `XRAY_SECURITY`    | `tls` или `none`                                          |
| `XRAY_NETWORK`     | `tcp`, `ws`, `grpc`                                       |
| `XRAY_API_ENABLED` | `true` / `false`                                          |
| `XRAY_API_LISTEN`  | Адрес, где XRay слушает API (`0.0.0.0` для Linux)         |
| `XRAY_API_HOST`    | Адрес, куда бот подключается (внешний IP или `127.0.0.1`) |
| `XRAY_API_PORT`    | Порт API (по умолчанию `10085`)                           |
| `XRAY_INBOUND_TAG` | Тег inbound-а в XRay                                      |

> ⚠️ Для Linux-сервера укажи:
> `XRAY_API_LISTEN=0.0.0.0`
> `XRAY_API_HOST=<внешний_IP_или_127.0.0.1>`
> и добавь `network_mode: "host"` в `docker-compose.yml`.

---

## 🐳 Docker-развёртывание

```bash
make docker-build
docker compose up -d
docker compose logs -f bot
```

### Примечание для Linux

Добавь в `docker-compose.yml` блок:

```yaml
services:
  bot:
    network_mode: "host"
```

Это позволит контейнеру напрямую видеть XRay API и интернет (без `host.docker.internal`).

---

## 🔧 Автоматизация (Ubuntu)

### scripts/setup_ubuntu.py

Готовит сервер: ставит Docker, настраивает UFW, создаёт пользователя.

```bash
sudo python3 scripts/setup_ubuntu.py --admin vpppn --ports 443 10085
```

### scripts/install_xray_service.py

Создаёт systemd-юнит для XRay:

```bash
sudo python3 scripts/install_xray_service.py --exec /usr/local/bin/xray --config /etc/xray/config.json
```

---

## ☑️ Полное развёртывание на сервере

### 1. Проверка связи

```bash
ping -c 3 8.8.8.8
curl https://api.telegram.org
```

### 2. Подготовка XRay

```bash
sudo mkdir -p /etc/xray /var/log/xray
sudo curl -L https://github.com/XTLS/Xray-core/releases/download/v25.10.15/Xray-linux-64.zip -o /tmp/xray.zip
sudo apt install -y unzip && sudo unzip /tmp/xray.zip -d /usr/local/share/xray
sudo install -m 755 /usr/local/share/xray/xray /usr/local/bin/xray
sudo python3 scripts/install_xray_service.py --exec /usr/local/bin/xray --config /etc/xray/config.json
```

### 3. Настройка проекта

```bash
git clone https://github.com/ibras0696/new_vpn.git
cd new_vpn
cp .env.example .env
nano .env
```

Минимальные поля:

```
BOT_TOKEN=<твой_токен>
ADMIN_ID=<твой_id>
XRAY_DOMAIN=141.98.235.192
XRAY_API_ENABLED=true
XRAY_API_LISTEN=0.0.0.0
XRAY_API_HOST=141.98.235.192
XRAY_API_PORT=10085
```

---

### 4. Запуск

```bash
docker compose up -d --build
```

После запуска:

```bash
sudo mkdir -p /etc/xray
sudo cp ./etc/xray/config.json /etc/xray/config.json
sudo systemctl restart xray
sudo ss -ltnp | grep 10085
```

Должно быть: `*:10085 (LISTEN)`

---

### 5. Проверка API из контейнера

```bash
docker compose exec bot sh -c "apt update -qq && apt install -y netcat-openbsd && nc -vz 141.98.235.192 10085"
```

Ожидаем:

```
Connection to 141.98.235.192 10085 port [tcp/*] succeeded!
```

---

### 6. Проверка работы бота

* Открой Telegram → `/start`
* Создай тестовый ключ → должен появиться QR и ссылка без ошибок `failed to dial`.

---

## 🧪 Тестирование

```bash
make test
```

## 🩺 Отладка

```bash
docker compose logs -f bot
journalctl -u xray -f
```

---

## 🧾 Лицензия

MIT © 2025. Contributions welcome.

---

Хочешь, я сразу сделаю diff-версию (`git patch`), чтобы ты просто применил её через `git apply` и не правил вручную?
