import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from data.models import VlessKey
from config import settings

logger = logging.getLogger(__name__)


class XRayAPIError(RuntimeError):
    """Исключение, описывающее ошибку вызова xray api."""

    def __init__(self, cmd: list[str], returncode: int, stdout: str, stderr: str) -> None:
        message = stderr.strip() or stdout.strip() or "xray api вернул ненулевой код."
        super().__init__(f"{' '.join(cmd)} -> {returncode}: {message}")
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _api_server() -> str:
    return f"{settings.XRAY_API_HOST}:{settings.XRAY_API_PORT}"


def _run_xray_api(command: str, *params: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """
    Вызывает бинарь xray с подкомандой api.
    Бросает исключение при ошибке и возвращает CompletedProcess.
    """
    cmd = ["xray", "api", command, f"--server={_api_server()}", *params]
    logger.debug("Выполняю команду: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        logger.error("Бинарь xray не найден в PATH: %s", exc)
        raise

    if check and result.returncode != 0:
        logger.error("Команда %s завершилась ошибкой:\nSTDOUT: %s\nSTDERR: %s", cmd, result.stdout, result.stderr)
        raise XRayAPIError(cmd, result.returncode, result.stdout, result.stderr)

    return result


def check_xray_api() -> bool:
    """
    Проверяет доступность XRay API.
    """
    try:
        _run_xray_api("lsi", "--isOnlyTags=true")
        return True
    except (FileNotFoundError, XRayAPIError) as exc:
        logger.warning("XRay API недоступен: %s", exc)
        return False


def _build_inbound_payload(vless_key: VlessKey, email: str) -> dict:
    """
    Формирует минимальный inbound-конфиг, который понимает утилита `xray api adu`.
    """
    inbound = {
        "inbounds": [
            {
                "tag": settings.XRAY_INBOUND_TAG,
                "protocol": "vless",
                "port": settings.XRAY_PORT,
                "settings": {
                    "clients": [
                        {
                            "id": str(vless_key.id),
                            "email": email,
                        }
                    ],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": settings.XRAY_NETWORK,
                    "security": settings.XRAY_SECURITY,
                },
            }
        ]
    }

    # Для tcp без tls поле security опционально — удаляем для чистоты.
    if settings.XRAY_SECURITY == "none":
        inbound["inbounds"][0]["streamSettings"].pop("security", None)
    return inbound


def add_vless_user(vless_key: VlessKey, email: str | None = None) -> bool:
    """
    Добавляет клиента VLESS через API XRay.
    :return: True, если добавление прошло успешно, False, если клиент уже существует.
    """
    email = email or str(vless_key.id)
    payload = _build_inbound_payload(vless_key, email)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(payload, tmp)
        tmp_path = Path(tmp.name)

    try:
        _run_xray_api("adu", str(tmp_path))
        logger.info("Добавлен VLESS-пользователь %s (email=%s)", vless_key.id, email)
        return True
    except XRayAPIError as exc:
        message = (exc.stderr or exc.stdout).lower()
        if "already existed" in message or "duplicate" in message or "exists" in message:
            logger.debug("VLESS-пользователь %s уже существует в XRay.", email)
            return False
        raise
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass


def remove_vless_user(email: str, ignore_missing: bool = True) -> bool:
    """
    Удаляет клиента VLESS через API XRay.

    :param email: Email, который выступает идентификатором пользователя в XRay.
    :param ignore_missing: Если True, отсутствие пользователя не считается ошибкой.
    :return: True, если пользователь удалён, False, если его не было.
    """
    try:
        _run_xray_api("rmu", f"--tag={settings.XRAY_INBOUND_TAG}", email)
        logger.info("Удалён VLESS-пользователь с email=%s", email)
        return True
    except XRayAPIError as exc:
        payload = (exc.stderr or exc.stdout or "").lower()
        if ignore_missing and ("not found" in payload or "no such user" in payload):
            logger.debug("Пользователь %s отсутствовал в XRay.", email)
            return False
        raise


async def reconcile_active_keys() -> None:
    """
    Синхронизирует активные ключи из базы данных с XRay.
    """
    from data.db import AsyncSessionLocal  # локальный импорт, чтобы избежать циклов
    from data.repo import VlessKeyRepo

    available = await asyncio.to_thread(check_xray_api)
    if not available:
        logger.warning("Пропуск синхронизации — XRay API недоступен.")
        return

    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        keys = await repo.list_all(only_active=True)

    if not keys:
        logger.info("Активных VLESS-ключей нет — синхронизация не требуется.")
        return

    logger.info("Синхронизация %s активных VLESS-ключей с XRay...", len(keys))
    for key in keys:
        try:
            await asyncio.to_thread(add_vless_user, key, str(key.id))
        except FileNotFoundError:
            logger.exception("Не удалось вызвать XRay CLI — бинарь отсутствует.")
            break
        except XRayAPIError:
            logger.exception("Ошибка при синхронизации ключа %s с XRay.", key.id)
            continue
