import logging
from html import escape
from pathlib import Path

from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

router = Router()
logger = logging.getLogger(__name__)
WELCOME_IMAGE = Path(__file__).resolve().parent.parent / "welcome.png"


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


def _new_member_welcome_caption(member: types.User) -> str:
    display_name = f"@{member.username}" if member.username else member.full_name
    mention = (
        f'<a href="tg://user?id={member.id}">{escape(display_name)}</a>'
    )
    return (
        f"👑 Welcome to the MCN Kingdom, {mention}! 🐾💙\n\n"
        "Your journey starts here.\n\n"
        "🤖 Meet the official MCN Bot and explore the Kingdom:\n\n"
        "🐾 Discover Oria, the Guardians & our lore\n"
        "📊 Explore MCN market data & on-chain info\n"
        "🏛️ Answer Vault questions and earn Guardian Energy\n"
        "🎟️ Check your eligibility for the MCN Hold Contest\n\n"
        "🔵 Ready to enter the Kingdom?\n\n"
        "👉 Open the MCN Bot to begin!\n\n"
        "🔐 Never share your private key or seed phrase.\n\n"
        "The Vault is filling. Oria is watching. 👀💎"
    )


@router.message(F.new_chat_members)
async def welcome_new_members(message: types.Message):
    members = [member for member in message.new_chat_members if not member.is_bot]
    if not members:
        return

    try:
        bot_user = await message.bot.get_me()
    except TelegramAPIError:
        logger.exception(
            "Could not prepare new-member welcome in chat %s",
            message.chat.id,
        )
        return
    if not bot_user.username:
        logger.error("Cannot post new-member welcome: bot username is unavailable.")
        return

    for member in members:
        try:
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=FSInputFile(WELCOME_IMAGE),
                caption=_new_member_welcome_caption(member),
                parse_mode="HTML",
                reply_markup=_welcome_keyboard(bot_user.username),
            )
        except TelegramAPIError:
            logger.exception(
                "Could not post new-member welcome for user %s in chat %s",
                member.id,
                message.chat.id,
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
        await update.bot.send_photo(
            update.chat.id,
            photo=FSInputFile(WELCOME_IMAGE),
            caption=(
                "👑 Welcome to the MCN Kingdom Portal!\n\n"
                "Welcome, Guardian! 🐾💙\n\n"
                "I’m the official MCN Bot, created especially for the MCN community.\n\n"
                "Explore the Kingdom and discover what awaits you:\n\n"
                "🐾 Meet Oria and the Guardians\n"
                "📜 Discover the MCN lore and ranks\n"
                "📊 Check MCN market data\n"
                "🔐 Explore token information and on-chain verification\n"
                "🏛️ Answer Vault questions and earn Guardian Energy\n"
                "🎟️ Register for the MCN Hold Contest\n\n"
                "🎟️ DRAW REGISTRATION\n\n"
                "Use /draw in my private chat to submit your public Base wallet "
                "address. I’ll check your MCN balance against the current $10 minimum.\n\n"
                "A current balance check does not prove continuous holding. "
                "Never share your private key or seed phrase.\n\n"
                "👑 Start your journey with /start in my private chat.\n\n"
                "The group is where Guardians connect. The bot is where your "
                "journey begins.\n\n"
                "The Vault is filling. Oria is watching. 👀"
            ),
            reply_markup=_welcome_keyboard(bot_user.username),
        )
    except TelegramAPIError:
        logger.exception(
            "Could not post MCN Kingdom welcome after bot promotion in chat %s",
            update.chat.id,
        )
