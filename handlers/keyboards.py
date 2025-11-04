from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать ключ", callback_data="menu:create")
    builder.button(text="📋 Список ключей", callback_data="menu:list")
    builder.button(text="🗑️ Удалить ключ", callback_data="menu:delete")
    builder.adjust(1)
    return builder.as_markup()


def create_key_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="7 дней", callback_data="create:days:7")
    builder.button(text="30 дней", callback_data="create:days:30")
    builder.button(text="90 дней", callback_data="create:days:90")
    builder.button(text="♾️ Бессрочный", callback_data="create:days:0")
    builder.button(text="✏️ Ввести своё число", callback_data="create:custom")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def back_to_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ В главное меню", callback_data="menu:main")
    return builder.as_markup()


def cancel_input_kb(tag: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data=f"cancel:{tag}")
    return builder.as_markup()


def key_created_actions_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать ещё", callback_data="menu:create")
    builder.button(text="⬅️ В главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()
