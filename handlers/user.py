from aiogram import types, Router
from aiogram.filters import Command

from db import ensure_user
from handlers.navigation import send_home

router = Router()


@router.message(Command("start"))
async def start(msg: types.Message):
    await ensure_user(msg.from_user)
    await send_home(msg)