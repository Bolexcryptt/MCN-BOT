from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db import ensure_user, get_invite_stats
from handlers.navigation import back_keyboard, send_screen

router = Router()


@router.message(Command("invite"))
async def invite(msg: types.Message):
    await show_invite(msg, msg.from_user)


async def show_invite(message: types.Message, user: types.User):
    await ensure_user(user)
    bot = await message.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user.id}"
    recruits, energy = await get_invite_stats(user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧲 INVITE GUARDIAN", url=link)],
            *back_keyboard().inline_keyboard,
        ]
    )
    text = (
        "🧲 GUARDIAN RECRUITMENT\n\n"
        "Bring another Guardian into the system.\n\n"
        f"👥 Guardians recruited: {recruits}\n"
        f"⚡ Energy earned from recruitment: +{energy}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Your recruitment link is ready. Each new Guardian can be counted once."
    )
    await send_screen(message, text, keyboard, "Guardian Recruitment")
