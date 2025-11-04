import json
import os
import subprocess
from data.models import VlessKey
from config import settings

XRAY_CONFIG_PATH = "/etc/xray/config.json"  # или свой путь


def _load_config() -> dict:
    """Читает текущий конфиг XRay."""
    if not os.path.exists(XRAY_CONFIG_PATH):
        raise FileNotFoundError(f"Файл {XRAY_CONFIG_PATH} не найден.")
    with open(XRAY_CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    """Сохраняет изменённый конфиг и перезапускает сервис XRay."""
    with open(XRAY_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    subprocess.run(["systemctl", "restart", "xray"], check=True)


def add_vless_user(vless_key: VlessKey, email: str = "autobot@vpn.local"):
    """
    Добавляет клиента VLESS в XRay config.json и перезапускает сервис.

    :param vless_key: ORM-объект ключа VlessKey.
    :param email: Идентификатор в XRay (обычно email для удобства логов).
    """
    config = _load_config()
    for inbound in config["inbounds"]:
        if inbound["protocol"] == "vless":
            inbound["settings"]["clients"].append({
                "id": str(vless_key.id),
                "email": email
            })
    _save_config(config)


def remove_vless_user(key_id: str):
    """Удаляет клиента по UUID из конфига и перезапускает сервис."""
    config = _load_config()
    for inbound in config["inbounds"]:
        if inbound["protocol"] == "vless":
            clients = inbound["settings"]["clients"]
            inbound["settings"]["clients"] = [c for c in clients if c["id"] != key_id]
    _save_config(config)
