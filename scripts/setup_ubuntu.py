#!/usr/bin/env python3
"""
Автоматическая подготовка Ubuntu Server 22.04/24.04:
 - обновление системы
 - установка тулчейна (curl, git, unzip, ufw)
 - установка Docker Engine + Compose plugin
 - создание пользователя для приложения (опционально)
 - настройка UFW с нужными портами

Запускать с sudo:
    sudo python3 scripts/setup_ubuntu.py --admin ibragim --ports 443 10085
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

APT_PACKAGES = [
    "curl",
    "git",
    "make",
    "unzip",
    "ufw",
    "ca-certificates",
    "gnupg",
    "lsb-release",
]

DOCKER_REPO_SETUP = [
    'install -m 0755 -d /etc/apt/keyrings',
    'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
    'chmod a+r /etc/apt/keyrings/docker.gpg',
    'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] '
    'https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" '
    '| tee /etc/apt/sources.list.d/docker.list > /dev/null',
]

DOCKER_PACKAGES = [
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-buildx-plugin",
    "docker-compose-plugin",
]


def run(cmd: Iterable[str | Path], check: bool = True) -> None:
    command = [str(c) for c in cmd]
    print(f"→ Выполняю: {' '.join(command)}")
    subprocess.run(command, check=check)


def ensure_root() -> None:
    if os.geteuid() != 0:
        print("Скрипт требует запуска от root. Используй sudo.", file=sys.stderr)
        sys.exit(1)


def install_packages(packages: Iterable[str]) -> None:
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", *packages])


def install_docker() -> None:
    for cmd in DOCKER_REPO_SETUP:
        run(["bash", "-lc", cmd])
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", *DOCKER_PACKAGES])


def add_user(username: str) -> None:
    run(["useradd", "-m", "-s", "/bin/bash", username])
    run(["usermod", "-aG", "sudo", username])
    run(["usermod", "-aG", "docker", username])


def configure_ufw(ports: Iterable[int]) -> None:
    run(["ufw", "allow", "OpenSSH"])
    for port in ports:
        run(["ufw", "allow", f"{port}/tcp"])
    run(["ufw", "--force", "enable"])
    run(["ufw", "status"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Подготовка Ubuntu сервера под VPPPN.")
    parser.add_argument("--admin", help="Создать системного пользователя для бота.")
    parser.add_argument(
        "--ports",
        nargs="*",
        type=int,
        default=[443, 10085],
        help="Порты, которые нужно открыть в UFW.",
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Пропустить установку Docker (если он уже установлен).",
    )
    return parser.parse_args()


def main() -> None:
    ensure_root()
    args = parse_args()

    print("=== Установка базовых пакетов ===")
    install_packages(APT_PACKAGES)

    if not args.skip_docker:
        print("=== Установка Docker Engine ===")
        install_docker()
    else:
        print("Пропускаю установку Docker по запросу.")

    if args.admin:
        print(f"=== Создание пользователя {args.admin} ===")
        add_user(args.admin)

    print("=== Настройка UFW ===")
    configure_ufw(args.ports)

    print("\nГотово! Перезайди в систему, чтобы обновить группы пользователя.")


if __name__ == "__main__":
    main()
