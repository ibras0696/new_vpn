from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_custom_days = State()
    waiting_delete_id = State()
