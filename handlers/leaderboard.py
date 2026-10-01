from aiogram import types, Router
from aiogram.filters import Command

from db import ensure_user, get_leaderboard
from handlers.navigation import back_keyboard

router = Router()


@router.message(Command("leaderboard"))
async def leaderboard(msg: types.Message):
    await ensure_user(msg.from_user)
    users = await get_leaderboard(10)

    if not users:
        await msg.answer("""
🏛️ THE VAULT RANKINGS

No Guardians have risen yet 👁️
Be the first to gain energy ⚡
""", reply_markup=back_keyboard())
        return

    medals = ["🥇", "🥈", "🥉"]
    text = "🏛️ THE VAULT RANKINGS\n\n"

    for i, (username, energy, vaults) in enumerate(users[:10], 1):
        medal = medals[i - 1] if i <= 3 else "#"
        display_name = username if username and username.startswith("@") else f"@{username or 'Guardian'}"
        rank_label = f"{medal} #{i}" if i <= 3 else f"#{i}"

        text += f"{rank_label} {display_name}\n"
        text += f"⚡ {energy:,} Energy\n"
        text += f"🛡️ {vaults} Vaults\n\n"

    await msg.answer(text, reply_markup=back_keyboard())