import logging
from datetime import datetime, timezone

from aiogram import types, Router
from aiogram.filters import Command

from aiogram.exceptions import TelegramAPIError

from db import ensure_user, record_referral
from handlers.navigation import send_home

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def start(msg: types.Message):
    await ensure_user(msg.from_user)
    parts = (msg.text or "").split(maxsplit=1)
    if (
        len(parts) == 2
        and parts[1].isascii()
        and parts[1].isdigit()
        and len(parts[1]) <= 19
        and int(parts[1]) <= 9_223_372_036_854_775_807
    ):
        inviter_id = int(parts[1])
        was_referred = await record_referral(
            msg.from_user.id,
            inviter_id,
            datetime.now(timezone.utc).date().isoformat(),
        )
        if was_referred:
            try:
                await msg.bot.send_message(
                    inviter_id,
                    "✨ A new Guardian joined through your recruitment link.\n⚡ +50 Energy",
                )
            except TelegramAPIError:
                logger.warning("Could not notify Guardian %s about a new referral", inviter_id)
    await send_home(msg)