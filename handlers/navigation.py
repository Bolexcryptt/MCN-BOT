from io import BytesIO

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont

router = Router()

HOME_TEXT = (
    "🐾 MCN GUARDIAN SYSTEM\n\n"
    "👁️ Oria is watching.\n"
    "Your path through the Vault begins here."
)

_ART_CACHE: dict[str, bytes] = {}


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏛️ ENTER VAULT", callback_data="hub:vault")],
            [InlineKeyboardButton(text="⚡ TRIALS", callback_data="hub:trials"),
             InlineKeyboardButton(text="👤 PROFILE", callback_data="hub:profile")],
            [InlineKeyboardButton(text="🏆 LEADERBOARD", callback_data="hub:leaderboard"),
             InlineKeyboardButton(text="🧲 INVITE", callback_data="hub:invite")],
            [InlineKeyboardButton(text="🔥 DAILY ACTIVITY", callback_data="hub:daily")],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")]
        ]
    )


def _make_artwork(label: str) -> bytes:
    if label in _ART_CACHE:
        return _ART_CACHE[label]

    image = Image.new("RGB", (900, 360), (5, 13, 29))
    draw = ImageDraw.Draw(image)
    for x in range(900):
        blue = int(28 + 35 * (1 - abs(x - 450) / 450))
        draw.line((x, 0, x, 360), fill=(5, 13 + blue // 5, 24 + blue // 2))

    for x in range(35, 900, 55):
        draw.line((x, 0, x, 360), fill=(11, 36, 61), width=1)
    for y in range(25, 360, 55):
        draw.line((0, y, 900, y), fill=(11, 36, 61), width=1)

    draw.ellipse((570, 24, 870, 324), outline=(17, 89, 138), width=3)
    draw.ellipse((603, 57, 837, 291), outline=(24, 121, 176), width=2)
    draw.ellipse((636, 90, 804, 258), outline=(39, 171, 221), width=2)
    draw.polygon([(720, 117), (774, 174), (720, 231), (666, 174)],
                 outline=(100, 214, 255), width=3)
    draw.ellipse((706, 160, 734, 188), fill=(72, 199, 255))
    draw.rectangle((36, 34, 49, 326), fill=(25, 158, 229))

    font = ImageFont.load_default()
    draw.text((72, 100), "MCN // THE VAULT", font=font, fill=(99, 205, 255))
    draw.text((72, 154), label.upper()[:28], font=font, fill=(224, 244, 255))
    draw.text((72, 198), "ORIA IS WATCHING", font=font, fill=(103, 147, 183))
    output = BytesIO()
    image.save(output, format="PNG")
    artwork = output.getvalue()
    _ART_CACHE[label] = artwork
    return artwork


async def send_screen(
    message: types.Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    artwork: str = "Guardian Hub",
):
    answer_photo = getattr(message, "answer_photo", None)
    if answer_photo is not None:
        await answer_photo(
            photo=BufferedInputFile(_make_artwork(artwork), filename="mcn-vault.png"),
            caption=text,
            reply_markup=reply_markup,
        )
    else:
        await message.answer(text, reply_markup=reply_markup)


async def send_home(message: types.Message):
    await send_screen(message, HOME_TEXT, home_keyboard(), "Guardian Hub")


@router.message(Command("menu"))
async def open_menu(message: types.Message):
    await send_home(message)


@router.callback_query(F.data == "navigation:home")
async def back_to_home(callback: types.CallbackQuery):
    await callback.answer()
    if callback.message:
        from handlers.vault import clear_user_session

        clear_user_session(callback.from_user.id)
        await send_home(callback.message)


@router.callback_query(F.data.startswith("hub:"))
async def open_hub_section(callback: types.CallbackQuery):
    if not callback.message or not callback.data:
        await callback.answer("This Guardian Hub action is unavailable.", show_alert=True)
        return

    from handlers import invite, leaderboard, profile, vault

    section = callback.data.partition(":")[2]
    handlers = {
        "vault": vault.show_vault,
        "trials": vault.show_trials,
        "profile": profile.show_profile,
        "leaderboard": leaderboard.show_leaderboard,
        "invite": invite.show_invite,
        "daily": vault.show_daily,
    }
    handler = handlers.get(section)
    if handler is None:
        await callback.answer("Unknown Guardian Hub action.", show_alert=True)
        return

    await callback.answer()
    await handler(callback.message, callback.from_user)
