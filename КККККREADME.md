Отлично 💪
Сделаем полностью **правильный README.md (v1.2 — production edition)**,
который реально можно использовать на чистом **Ubuntu-сервере**, чтобы **развернуть всё от нуля до рабочего Telegram-бота + XRay API**.

---

📄 Ниже — финальный, откорректированный текст файла.
После проверки я сгенерирую тебе `README.md`, готовый для скачивания.

---

# new_vpn — Telegram-бот для управления VLESS-ключами (XRay API)

Бот помогает администратору выдавать, просматривать и отзывать VLESS-ключи для **XRay**.
Ключи публикуются в Telegram одним нажатием с QR-кодом, а состояние XRay синхронизируется через API.

---

## 🚀 Возможности

* Создание и удаление VLESS-ключей через Telegram-меню.
* QR-код и VLESS-ссылка одним нажатием.
* Автоматическая регистрация клиентов в XRay API.
* Планировщик удаления просроченных ключей.
* Health-check XRay при старте.
* Скрипты быстрой установки Docker и XRay на Ubuntu.

---

## 📦 Структура проекта

```
handlers/          # Хендлеры и клавиатуры aiogram
services/          # Интеграция с XRay и планировщик
data/              # async SQLAlchemy ORM
filters/           # Кастомные фильтры aiogram
scripts/           # setup_ubuntu.py / install_xray_service.py
etc/xray/          # шаблон конфига config.dev.json
tests/             # PyTest сценарии для API
Dockerfile         # образ Telegram-бота
docker-compose.yml # контейнер bot
Makefile           # команды сборки и запуска
pyproject.toml     # зависимости и метаданные
```

---

## 🧾 Требования

* Ubuntu **22.04 / 24.04** с интернетом и root-доступом.
* Python ≥ 3.11, Git, Make, Docker, Docker Compose.
* Telegram Bot API токен и ID администратора.
* XRay Core (устанавливается на этом же сервере).

---

## 🧰 Установка: пошагово

### Этап 0. Проверка связи

```bash
ping -c 3 8.8.8.8
curl https://api.telegram.org
nslookup registry-1.docker.io
```

Если есть проблемы — настрой DNS, например:

```bash
sudo nano /etc/systemd/resolved.conf
# добавь строку:
DNS=1.1.1.1 8.8.8.8
sudo systemctl restart systemd-resolved
```

---

### Этап 1. Установка Docker и зависимостей

#### Вариант A — через скрипт

```bash
curl -fsSL https://raw.githubusercontent.com/ibras0696/new_vpn/main/scripts/setup_ubuntu.py -o /tmp/setup_ubuntu.py
sudo python3 /tmp/setup_ubuntu.py --admin vpppn --ports 443 10085
```

Скрипт:

* обновит систему и поставит `git`, `curl`, `docker`, `ufw`;
* создаст пользователя `vpppn`;
* откроет порты 443 (VLESS) и 10085 (XRay API).

#### Вариант B — вручную

```bash
sudo apt update && sudo apt install -y git make curl unzip ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo ufw allow OpenSSH
sudo ufw allow 443/tcp
sudo ufw allow 10085/tcp
sudo ufw enable
```

---

### Этап 2. Установка XRay Core

```bash
sudo mkdir -p /etc/xray /var/log/xray
curl -L https://github.com/XTLS/Xray-core/releases/download/v25.10.15/Xray-linux-64.zip -o /tmp/xray.zip
sudo apt install -y unzip
sudo unzip /tmp/xray.zip -d /usr/local/share/xray
sudo install -m 755 /usr/local/share/xray/xray /usr/local/bin/xray
```

Создаём и запускаем systemd-юнит:

```bash
curl -fsSL https://raw.githubusercontent.com/ibras0696/new_vpn/main/scripts/install_xray_service.py -o /tmp/install_xray_service.py
sudo python3 /tmp/install_xray_service.py \
  --exec /usr/local/bin/xray \
  --config /etc/xray/config.json
```

Проверяем:

```bash
sudo systemctl status xray
```

---

### Этап 3. Клонирование проекта и настройка окружения

```bash
cd /opt
sudo git clone https://github.com/ibras0696/new_vpn.git
cd new_vpn
sudo cp .env.example .env
sudo mkdir -p etc/xray
sudo cp etc/xray/config.dev.json /etc/xray/config.json
```

Отредактируй `.env`:

```bash
sudo nano .env
```

Пример для продакшена:

```
BOT_TOKEN=<ТВОЙ_ТОКЕН>
ADMIN_ID=<ТВОЙ_ID>
XRAY_CONFIG_PATH=/etc/xray/config.json
XRAY_DOMAIN=141.98.235.192
XRAY_PORT=443
XRAY_SECURITY=none
XRAY_NETWORK=tcp
XRAY_API_ENABLED=true
XRAY_API_LISTEN=0.0.0.0
XRAY_API_HOST=141.98.235.192
XRAY_API_PORT=10085
XRAY_INBOUND_TAG=vless-inbound
```

---

### Этап 4. Настройка Docker

Открой `docker-compose.yml`:

```bash
nano docker-compose.yml
```

и добавь:

```yaml
network_mode: "host"
```

Пример итогового файла:

```yaml
version: "3.9"
services:
  bot:
    build:
      context: .
    image: vpppn-bot:latest
    env_file:
      - .env
    command: ["python", "-m", "main"]
    restart: unless-stopped
    network_mode: "host"
    volumes:
      - ./data:/app/data
      - ./etc/xray:/etc/xray
```

---

### Этап 5. Сборка и запуск контейнера

```bash
make docker-build
docker compose up -d --build
docker compose logs -f bot
```

---

### Этап 6. Проверка XRay API

Проверь, слушает ли XRay порт 10085:

```bash
sudo ss -ltnp | grep 10085
```

Ожидаем:

```
LISTEN ... *:10085 ...
```

Проверь соединение из контейнера:

```bash
docker compose exec bot python - <<'PY'
import socket
socket.create_connection(('141.98.235.192', 10085), timeout=3)
print("✅ XRay API доступен")
PY
```

Если видишь `✅`, значит всё готово.

---

### Этап 7. Проверка бота

* В Telegram напиши `/start` с ID администратора.
* Создай тестовый ключ — должен появиться QR-код и ссылка.
* В логах бота (`docker compose logs -f bot`) не должно быть `failed to dial`.

---

## 🧪 Тестирование

```bash
make test
```

PyTest проверяет взаимодействие с XRay API и обработку ошибок.

---

## 🩺 Отладка

```bash
docker compose logs -f bot
journalctl -u xray -f
```

---

## ⚙️ Полезные команды

| Команда                       | Действие                        |
| ----------------------------- | ------------------------------- |
| `make run`                    | Локальный запуск без Docker     |
| `make docker-build`           | Сборка Docker-образа            |
| `docker compose ps`           | Проверить запущенные контейнеры |
| `docker compose restart bot`  | Перезапустить бот               |
| `sudo systemctl restart xray` | Перезапустить XRay              |
| `sudo journalctl -u xray -f`  | Смотреть логи XRay              |

---

## 🔒 Безопасность

* Не открывай порт `10085` в интернет.
* Разреши доступ только из localhost (бот и XRay на одном сервере).
* Храни `.env` отдельно, не коммить в репозиторий.

---

## 🧾 Лицензия

MIT © 2025
Разработка и поддержка: [@ibras0696](https://github.com/ibras0696)

---
