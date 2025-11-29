from __future__ import annotations

import ipaddress
import subprocess
from dataclasses import dataclass
from typing import Iterable

from app.config import Settings


@dataclass
class WireGuardCredentials:
    """Набор данных для клиента WireGuard.

    :param private_key: приватный ключ клиента.
    :param public_key: публичный ключ клиента.
    :param client_address: выделенный адрес в туннельной подсети.
    :param preshared_key: опциональный предварительно разделяемый ключ.
    :param config_text: финальный текст конфигурации клиента.
    """

    private_key: str
    public_key: str
    client_address: str
    preshared_key: str | None
    config_text: str


def _run_cmd(args: list[str], input_data: str | None = None) -> str:
    """Выполняет команду и возвращает stdout без переносов.

    :param args: список аргументов.
    :param input_data: опциональные данные для stdin.
    :return: stdout с обрезанным концом строки.
    """

    return subprocess.check_output(args, input=input_data, text=True).strip()


def generate_keypair() -> tuple[str, str]:
    """Генерирует пару ключей WireGuard через wireguard-tools.

    :return: кортеж (private, public).
    :raises CalledProcessError: если утилита wg недоступна.
    """

    private_key = _run_cmd(["wg", "genkey"])
    public_key = _run_cmd(["wg", "pubkey"], input_data=f"{private_key}\n")
    return private_key, public_key


def generate_preshared_key() -> str:
    """Генерирует предварительно разделяемый ключ.

    :return: psk строка.
    """

    return _run_cmd(["wg", "genpsk"])


def build_client_config(
    private_key: str,
    client_address: str,
    settings: Settings,
    preshared_key: str | None,
) -> str:
    """Формирует конфиг клиента WireGuard.

    :param private_key: приватный ключ клиента.
    :param client_address: адрес клиента в туннеле.
    :param settings: конфигурация приложения.
    :param preshared_key: опциональный PSK.
    :return: текст конфигурации.
    """

    dns_line = ", ".join(settings.wg_dns)
    allowed_ips = ", ".join(sorted(settings.wg_allowed_ips))
    psk_line = f"PresharedKey = {preshared_key}\n" if preshared_key else ""
    return (
        "[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {client_address}\n"
        f"DNS = {dns_line}\n"
        "\n"
        "[Peer]\n"
        f"PublicKey = {settings.wg_server_public_key}\n"
        f"Endpoint = {settings.wg_endpoint}\n"
        f"AllowedIPs = {allowed_ips}\n"
        f"{psk_line}"
        "PersistentKeepalive = 25\n"
    )


def allocate_client_address(
    cidr: str,
    occupied: Iterable[str],
) -> str:
    """Подбирает свободный адрес в подсети для нового пира.

    :param cidr: строка подсети (например, 10.8.0.0/24).
    :param occupied: набор занятых адресов.
    :return: свободный IP в формате CIDR-адреса (ip/32 или ip/128).
    :raises ValueError: если свободных адресов нет.
    """

    network = ipaddress.ip_network(cidr, strict=False)
    occupied_set = {ipaddress.ip_interface(addr).ip for addr in occupied if addr}

    for host in network.hosts():
        if host in occupied_set:
            continue
        suffix = 128 if host.version == 6 else 32
        return f"{host}/{suffix}"
    raise ValueError("Нет свободных адресов в пуле WireGuard")
