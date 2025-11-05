import json
import os
from config import settings


def configure_xray():
    """
    Автоматически создаёт или обновляет XRay config.json
    на основе параметров из .env.
    """
    config_path = settings.XRAY_CONFIG_PATH
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    config = _build_config()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"✅ XRay config.json создан или обновлён: {config_path}")


def _build_config() -> dict:
    """Формирует структуру конфига XRay на основе settings."""

    base_config = {
        "log": {
            "access": "/var/log/xray/access.log",
            "error": "/var/log/xray/error.log",
            "loglevel": "info"
        },
        "inbounds": [
            {
                "port": settings.XRAY_PORT,
                "protocol": "vless",
                "tag": settings.XRAY_INBOUND_TAG,
                "settings": {
                    "clients": [],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": settings.XRAY_NETWORK,
                    "security": settings.XRAY_SECURITY
                }
            }
        ],
        "outbounds": [{"protocol": "freedom"}],
    }

    if settings.XRAY_API_ENABLED:
        base_config["api"] = {
            "services": ["HandlerService", "LoggerService", "StatsService"],
            "tag": "api"
        }
        base_config["inbounds"].append({
            "listen": settings.XRAY_API_LISTEN,
            "port": settings.XRAY_API_PORT,
            "protocol": "dokodemo-door",
            "settings": {"address": "127.0.0.1"},
            "tag": "api"
        })

    return base_config
