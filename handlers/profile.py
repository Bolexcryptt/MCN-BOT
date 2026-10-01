from aiogram import types, Router
from aiogram.filters import Command

from db import ensure_user, get_user
from handlers.navigation import back_keyboard

router = Router()


@router.message(Command("me"))
async def me(msg: types.Message):
    await ensure_user(msg.from_user)
    user_id = msg.from_user.id
    data = await get_user(user_id)

    if not data:
        await msg.answer("❌ Guardian not found. Try /start first.", reply_markup=back_keyboard())
        return

    username = data[1] or msg.from_user.first_name or "Guardian"
    display_name = username if username.startswith("@") else f"@{username}"
    energy = data[2] or 0
    vaults = data[6] or 0
    invites = data[5] or 0

    await msg.answer(f"""
👤 Guardian Profile

Name: {display_name}
⚡ Total Energy: {energy}
🛡️ Total Vaults Completed: {vaults}
👥 Guardians Invited: {invites}

Oria is watching 👁️
""", reply_markup=back_keyboard())