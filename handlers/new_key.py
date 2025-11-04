import io
import qrcode
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile  # ✅ Добавляем импорт
from config import settings
from data.db import AsyncSessionLocal
from data.repo import VlessKeyRepo

router = Router()


@router.message(Command("new_key"))
async def cmd_new_key(message: types.Message):
    """
    Создаёт новый VLESS-ключ, отправляет ссылку и QR-код для подключения.
    Формат ссылки:
        vless://<UUID>@<DOMAIN>:<PORT>?encryption=none&security=tls&type=tcp#VPN_KEY
    """
    if message.from_user.id != settings.ADMIN_ID:
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("⚠️ Использование: /new_key 'дней'\nНапример: /new_key 30 или /new_key 0 для бессрочного.")
        return

    try:
        days = int(parts[1])
        days = None if days == 0 else days
    except ValueError:
        await message.answer("❌ Укажи число дней. Пример: /new_key 30")
        return

    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        key = await repo.create(user_id=1, days=days)

    # === Формируем VLESS-ссылку ===
    domain = settings.XRAY_DOMAIN
    port = settings.XRAY_PORT
    network = settings.XRAY_NETWORK
    security = settings.XRAY_SECURITY

    vless_link = (
        f"vless://{key.id}@{domain}:{port}"
        f"?encryption=none&security={security}&type={network}#VPN_KEY"
    )

    # === Генерация QR-кода ===
    qr_img = qrcode.make(vless_link)
    qr_bytes = io.BytesIO()
    qr_img.save(qr_bytes, format="PNG")
    qr_bytes.seek(0)

    # ✅ Правильно: оборачиваем байты в BufferedInputFile
    qr_input = BufferedInputFile(qr_bytes.read(), filename="vless_qr.png")

    # === Формируем сообщение ===
    exp_text = "♾️ Бессрочный" if not key.expires_at else key.expires_at.strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f"✅ <b>Ключ создан!</b>\n\n"
        f"<b>ID:</b> <code>{key.id}</code>\n"
        f"<b>Срок:</b> {exp_text}\n"
        f"<b>Устройства:</b> {key.device_limit}\n\n"
        f"<b>VLESS ссылка:</b>\n<code>{vless_link}</code>\n\n"
        f"📱 Отсканируй QR-код ниже в <b>V2RayNG</b>, <b>Nekoray</b> или <b>v2rayN</b>."
    )

    await message.answer_photo(
        qr_input,            # ✅ Теперь это BufferedInputFile, не BytesIO
        caption=text,
        parse_mode="HTML"
    )
