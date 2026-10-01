from aiogram import types, Router
from aiogram.filters import Command, CommandStart

from data.store import user_invites, referrals
from db import add_invite, ensure_user
from handlers.navigation import back_keyboard

router = Router()


@router.message(Command("invite"))
async def invite(msg: types.Message):
    await ensure_user(msg.from_user)
    bot = await msg.bot.get_me()
    link = f"https://t.me/{bot.username}?start={msg.from_user.id}"

    await msg.answer(f"""
🧲 Invite a new Guardian

{link}

Earn rewards ⚡
""", reply_markup=back_keyboard())


@router.message(CommandStart())
async def start_ref(msg: types.Message, command: CommandStart):
    await ensure_user(msg.from_user)
    user_id = msg.from_user.id

    if command.args:
        inviter_id = int(command.args)

        if inviter_id != user_id and user_id not in referrals:
            referrals[user_id] = inviter_id
            user_invites[inviter_id] = user_invites.get(inviter_id, 0) + 1
            await add_invite(inviter_id)

            try:
                await msg.bot.send_message(
                    inviter_id,
                    "✨ A new Guardian joined through you\n🏦 +1 Vault contribution"
                )
            except Exception:
                pass