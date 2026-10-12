import logging

from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()
logger = logging.getLogger(__name__)


def _is_admin_status(status: str) -> bool:
    return status in {"administrator", "creator"}


def _welcome_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏰 Open MCN Kingdom",
                    url=f"https://t.me/{bot_username}?start=kingdom",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎟️ Enter the Draw",
                    url=f"https://t.me/{bot_username}?start=draw",
                )
            ],
        ]
    )


@router.my_chat_member()
async def welcome_when_promoted(update: types.ChatMemberUpdated):
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    if _is_admin_status(old_status) or not _is_admin_status(new_status):
        return

    try:
        bot_user = await update.bot.get_me()
        if not bot_user.username:
            logger.error("Cannot post Kingdom welcome: bot username is unavailable.")
            return
        await update.bot.send_message(
            update.chat.id,
            "👑 Welcome to the MCN Kingdom Portal!\n\n"
            "I’m the MCN bot, here to help the community explore the Kingdom and "
            "verify key token information.\n\n"
            "In the bot’s private chat, members can:\n"
            "🐾 Meet Oria and the Guardians\n"
            "📜 Explore MCN lore and ranks\n"
            "📊 Check live MCN market data\n"
            "🔐 Review token verification and safety information\n"
            "🏛️ Enter Vault questions and earn Guardian Energy\n"
            "🎟️ Register for the draw with a public Base wallet address\n\n"
            "For draw entry, use /draw in my private chat. I check the wallet’s "
            "MCN balance on Base and its estimated value against the $10 minimum. "
            "A current balance check does not prove continuous holding. "
            "Never share a private key or seed phrase.\n\n"
            "Use /start in my private chat to enter the Kingdom. This group stays "
            "for community conversation; interactive questions and wallet details "
            "stay private.",
            reply_markup=_welcome_keyboard(bot_user.username),
        )
    except TelegramAPIError:
        logger.exception(
            "Could not post MCN Kingdom welcome after bot promotion in chat %s",
            update.chat.id,
        )
