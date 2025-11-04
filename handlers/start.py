from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from config import settings
from filters.admin import AdminFilter
from .keyboards import main_menu_kb

router = Router()


@router.message(AdminFilter(), CommandStart())
@router.message(AdminFilter(), Command("menu"))
async def start_admin(message: Message):
    await message.answer(
        "Привет! Выбери действие 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(CommandStart())
async def start_guest(message: Message):
    await message.answer("⛔ У тебя нет доступа к этому боту.")


@router.callback_query(AdminFilter(), F.data == "menu:main")
async def back_to_main(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text(
            "Что делаем дальше?",
            reply_markup=main_menu_kb(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "Что делаем дальше?",
            reply_markup=main_menu_kb(),
        )
