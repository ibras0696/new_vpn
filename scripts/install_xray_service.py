#!/usr/bin/env python3
"""
Скрипт создаёт systemd unit для XRay и размещает файлы конфигурации.
По умолчанию предполагается, что бот сгенерирует /etc/xray/config.json.

Пример использования:
    sudo python3 scripts/install_xray_service.py \
        --user root \
        --exec /usr/local/bin/xray \
        --config /etc/xray/config.json
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

UNIT_TEMPLATE = """[Unit]
Description=XRay Service
After=network.target

[Service]
User={user}
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart={exec_path} run -config {config_path}
Restart=on-failure
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""


def ensure_root() -> None:
    if os.geteuid() != 0:
        print("Запусти скрипт от root или через sudo.", file=sys.stderr)
        sys.exit(1)


def run(cmd: list[str]) -> None:
    print(f"→ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def write_file(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.chmod(path, mode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Создание systemd юнита для XRay.")
    parser.add_argument("--user", default="root", help="Пользователь, от которого запускать сервис.")
    parser.add_argument("--exec", dest="exec_path", default="/usr/local/bin/xray", help="Путь к бинарю xray.")
    parser.add_argument("--config", dest="config_path", default="/etc/xray/config.json", help="Путь к конфигу.")
    parser.add_argument("--unit-path", default="/etc/systemd/system/xray.service", help="Куда сохранить unit файл.")
    parser.add_argument("--log-dir", default="/var/log/xray", help="Каталог для логов XRay.")
    parser.add_argument("--dry-run", action="store_true", help="Не записывать файлы, а только показать результат.")
    return parser.parse_args()


def main() -> None:
    ensure_root()
    args = parse_args()

    log_dir = Path(args.log_dir)
    config_path = Path(args.config_path)
    unit_path = Path(args.unit_path)

    print(f"Создаю каталог логов: {log_dir}")
    if not args.dry_run:
        log_dir.mkdir(parents=True, exist_ok=True)

    print(f"Генерирую unit файл: {unit_path}")
    unit_content = UNIT_TEMPLATE.format(
        user=args.user,
        exec_path=args.exec_path,
        config_path=config_path,
    )

    if args.dry_run:
        print("--- unit preview ---")
        print(unit_content)
        print("---------------------")
    else:
        write_file(unit_path, unit_content, 0o644)

    if args.dry_run:
        print("Dry-run завершён. Файлы не записаны.")
        return

    print("Перечитываю конфигурацию systemd...")
    run(["systemctl", "daemon-reload"])
    print("Включаю и запускаю сервис...")
    run(["systemctl", "enable", "--now", unit_path.name])
    print("Готово! Проверить статус: systemctl status xray")


if __name__ == "__main__":
    main()
