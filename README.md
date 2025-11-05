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
- Рабочий выход в интернет (проверь перед стартом: `ping 8.8.8.8`, `nslookup registry-1.docker.io`, `curl https://api.telegram.org`). Если команды падают — сначала исправь сеть/ DNS.
- Python 3.11+
- Git, Make (`sudo apt-get install -y git make` на Ubuntu, если скрипт ещё не ставил)
- Telegram Bot API токен
- XRay Core (CLI `xray`, API включённый inbound)
- SQLite (по умолчанию) или PostgreSQL

## Установка и запуск (локально)
1. Клонируй репозиторий `git clone https://github.com/ibras0696/new_vpn.git` и перейди в его каталог.
2. Создай виртуальное окружение (`python3 -m venv .venv`), активируй его и выполни `make dev-install`.
3. Скопируй `.env.example` в `.env`, заполни обязательные переменные.
4. Запусти бота командой `make run`.

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
1. **Проверка сети.** Убедись, что сервер выходит в интернет: `ping 8.8.8.8`, `nslookup registry-1.docker.io`, `curl https://api.telegram.org`. Если DNS не работает — пропиши публичные DNS (например, в `/etc/systemd/resolved.conf` выставь `DNS=1.1.1.1 8.8.8.8`, `FallbackDNS=1.0.0.1 8.8.4.4`, затем `sudo systemctl restart systemd-resolved`). Проверь, что firewall не блокирует исходящий трафик (`sudo ufw status verbose` → *Default: allow outgoing*).
2. **Базовая настройка.** Выполни `sudo python3 scripts/setup_ubuntu.py --admin <user> --ports 443 10085` (или поставь пакеты вручную: git, make, docker, ufw). После скрипта перезайди в сессию, чтобы применились группы docker/sudo.
3. **Клонирование и `.env`.** Клонируй репозиторий, зайди в каталог и создай `.env` на основе `.env.example`. Обязательно поставь:
   - `XRAY_DOMAIN` = внешний IP или домен сервера;
   - `XRAY_API_HOST` = тот же IP/домен (Docker будет ходить на него);  
   - `XRAY_API_LISTEN=0.0.0.0`, чтобы XRay слушал API на всех интерфейсах;  
   - остальные значения по ситуации (порт, TLS, БД).
4. **Запуск контейнера.** Выполни `docker compose up -d --build` (или `make compose-up`). После старта в каталоге появится `./etc/xray/config.json`.
5. **Применение конфига XRay.** Скопируй файл в системный путь и перезапусти службу:
   ```bash
   sudo cp ./etc/xray/config.json /etc/xray/config.json
   sudo systemctl restart xray
   sudo ss -ltnp | grep 10085  # должен показать 0.0.0.0:10085
   ```
6. **Проверка API из контейнера.**
   ```bash
   docker compose exec bot python - <<'PY'
import socket
socket.create_connection(('YOUR_SERVER_IP', 10085), timeout=3)
print('OK: API доступен')
PY
   ```
   Если соединение открывается — XRay готов к управлению. Если нет, вернись к шагу 5.
7. **Убедись, что бот запущен в единственном экземпляре.** `docker compose ps` должен показывать один контейнер `bot`. Если ранее запускал вручную (`python -m main`), останови процесс.
8. **Проверка Telegram.** В логах `docker compose logs -f bot` не должно быть `TelegramNetworkError` или `Conflict`. Если появляются — проверь интернет и наличие параллельных запусков.

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
