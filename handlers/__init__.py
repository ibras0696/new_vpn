from aiogram import Router

from .start import router as start
from .keys import router as keys
from .new_key import router as new_key

router = Router()

router.include_routers(start, keys, new_key)
