from aiogram import Router, types
from aiogram.filters import Command

from db import ensure_user, get_user, rank_for_energy
from handlers.navigation import back_keyboard, send_screen

router = Router()


@router.message(Command("me"))
async def me(msg: types.Message):
    await show_profile(msg, msg.from_user)


async def show_profile(message: types.Message, user: types.User):
    await ensure_user(user)
    data = await get_user(user.id)
    if not data:
        await send_screen(
            message,
            "❌ Guardian record unavailable. Please try /start again.",
            back_keyboard(),
            "Guardian Profile",
        )
        return

    display_name = (
        f"@{data[1]}" if data[1] else (data[7] or user.first_name or "Guardian")
    )
    energy = data[2] or 0
    vaults = data[6] or 0
    invites = data[5] or 0
    rank, next_threshold, current_threshold, _ = rank_for_energy(energy)
    if next_threshold is None:
        progress_text = "MAXIMUM RANK REACHED 👑"
        progress_bar = "██████████ 100%"
    else:
        percent = min(100, max(0, int(
            (energy - current_threshold) * 100 / (next_threshold - current_threshold)
        )))
        progress_bar = f"{'█' * (percent // 10)}{'░' * (10 - percent // 10)} {percent}%"
        progress_text = f"Progress toward {rank_for_energy(next_threshold)[0]}"

    text = (
        "🎖️ GUARDIAN PROFILE\n\n"
        f"{'Username' if data[1] else 'Name'}: {display_name}\n\n"
        f"🛡️ Rank: {rank}\n"
        f"📅 Joined: {data[18] if len(data) > 18 and data[18] else 'Legacy member'}\n"
        f"✨ Guardian XP: {energy:,}\n\n"
        "📊 Community activity\n"
        f"🏛️ Vaults completed: {vaults}\n"
        f"👥 Guardians invited: {invites}\n"
        f"🔥 Daily streak: {data[9] if len(data) > 9 and data[9] else 0} days\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{progress_text}\n{progress_bar}\n\n"
        "Earn XP through Vault trials, unlimited questions, daily activity and referrals."
    )
    await send_screen(message, text, back_keyboard(), "Guardian Profile")
