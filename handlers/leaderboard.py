from aiogram import Router, types
from aiogram.filters import Command

from db import ensure_user, get_leaderboard
from handlers.navigation import back_keyboard, send_screen

router = Router()


@router.message(Command("leaderboard"))
async def leaderboard(msg: types.Message):
    await show_leaderboard(msg, msg.from_user)


async def show_leaderboard(message: types.Message, user: types.User):
    await ensure_user(user)
    users = await get_leaderboard(10)
    if not users:
        text = (
            "🏛️ THE VAULT RANKINGS\n\n"
            "No Guardians have risen yet 👁️\n"
            "Be the first to gain Energy ⚡"
        )
        await send_screen(message, text, back_keyboard(), "Vault Rankings")
        return

    medals = ("🥇", "🥈", "🥉")
    entries = []
    for index, entry in enumerate(users, 1):
        username, energy, vaults = entry[:3]
        first_name = entry[3] if len(entry) > 3 else None
        display_name = f"@{username}" if username else (first_name or "Guardian")
        medal = medals[index - 1] if index <= len(medals) else f"#{index}"
        entries.append(f"{medal} {display_name}\n⚡ {energy:,} Energy\n🛡️ {vaults} Vaults")

    text = (
        "🏛️ THE VAULT RANKINGS\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(entries)
        + "\n\n━━━━━━━━━━━━━━━━━━\n\n"
        "👁️ Oria sees every Guardian."
    )
    await send_screen(message, text, back_keyboard(), "Vault Rankings")
