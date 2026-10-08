
from io import BytesIO
from pathlib import Path

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont

router = Router()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = PROJECT_ROOT

_ARTWORK_ASSET_MAP = {
    "guardian hub": ("kingdom1.png", "kingdom2.png", "kingdom3.png"),
    "guardian profile": ("guardians.png", "eliteguardians.png", "royalguardians.png"),
    "vault entrance": ("thevault.png", "vault2.png", "kingdom3.png"),
    "vault trial": ("vault2.png", "thevault.png", "kingdom4.png"),
    "vault trial complete": ("vault2.png", "thevault.png", "kingdom4.png"),
    "vault access": ("thevault.png", "vault2.png", "kingdom3.png"),
    "vault rankings": ("royalguardians.png", "eliteguardians.png", "guardians.png"),
    "vault signal": ("oria.png", "thevault.png", "vault2.png"),
    "guardian trial": ("kingdom3.png", "kingdom4.png", "kingdom2.png"),
    "guardian trials": ("kingdom4.png", "kingdom3.png", "kingdom2.png"),
    "daily guardian activity": ("kingdom3.png", "kingdom4.png", "kingdom2.png"),
    "guardian recruitment": ("mcnlogo.png", "mcntoken.png", "ambassador.png"),
    "mcn kingdom": ("mcnlogo.png", "mcntoken.png", "ambassador.png"),
    "oria": ("oria.png", "kingdom3.png", "kingdom4.png"),
    "guardians": ("guardians.png", "eliteguardians.png", "royalguardians.png"),
    "ambassador": ("ambassador.png", "royalguardians.png", "mcnlogo.png"),
    "rank progression": ("royalguardians.png", "eliteguardians.png", "ambassador.png"),
}

HOME_TEXT = (
    "👑 Welcome to the MCN Kingdom\n\n"
    "🐾 Meet Oria\n"
    "🛡️ Meet the Guardians\n"
    "💎 Discover MCN\n"
    "🔵 Explore Base\n"
    "🔐 Verify MCN\n"
    "📊 Track the Token\n"
    "🏆 Community & Rewards\n"
    "📜 Discover the Lore"
)

_ART_CACHE: dict[str, bytes] = {}


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐾 Meet Oria", callback_data="hub:oria")],
            [InlineKeyboardButton(text="🛡️ Meet the Guardians", callback_data="hub:guardians")],
            [InlineKeyboardButton(text="💎 Discover MCN", callback_data="hub:mcn")],
            [InlineKeyboardButton(text="🔵 Explore Base", callback_data="hub:live")],
            [InlineKeyboardButton(text="🔐 Verify MCN", callback_data="hub:verify")],
            [InlineKeyboardButton(text="📊 Track the Token", callback_data="hub:live")],
            [InlineKeyboardButton(text="🏆 Community & Rewards", callback_data="hub:rewards")],
            [InlineKeyboardButton(text="📜 Discover the Lore", callback_data="hub:lore")],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")]
        ]
    )


def _resolve_asset_path(label: str) -> str | None:
    normalized = (label or "").strip()
    if not normalized:
        return None

    lowered = normalized.casefold()
    for key, candidates in sorted(
        _ARTWORK_ASSET_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if key == lowered or key in lowered:
            for candidate in candidates:
                path = ASSET_DIR / candidate
                if path.is_file():
                    return str(path)
            break

    if "oria" in lowered:
        for candidate in ("oria.png", "kingdom3.png", "kingdom4.png"):
            path = ASSET_DIR / candidate
            if path.is_file():
                return str(path)
    if "vault" in lowered or "seal" in lowered:
        for candidate in ("thevault.png", "vault2.png", "kingdom3.png"):
            path = ASSET_DIR / candidate
            if path.is_file():
                return str(path)
    if "trial" in lowered:
        for candidate in ("vault2.png", "kingdom3.png", "kingdom4.png"):
            path = ASSET_DIR / candidate
            if path.is_file():
                return str(path)
    if "rank" in lowered or "ambassador" in lowered or "royal" in lowered:
        for candidate in ("royalguardians.png", "eliteguardians.png", "ambassador.png"):
            path = ASSET_DIR / candidate
            if path.is_file():
                return str(path)
    if "recruit" in lowered or "invite" in lowered or "mcn" in lowered:
        for candidate in ("mcnlogo.png", "mcntoken.png", "ambassador.png"):
            path = ASSET_DIR / candidate
            if path.is_file():
                return str(path)
    if "profile" in lowered or "guardians" in lowered:
        for candidate in ("guardians.png", "eliteguardians.png", "royalguardians.png"):
            path = ASSET_DIR / candidate
            if path.is_file():
                return str(path)
    return None


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
    asset_path = _resolve_asset_path(artwork)
    if answer_photo is not None and asset_path is not None:
        await answer_photo(
            photo=FSInputFile(asset_path),
            caption=text,
            reply_markup=reply_markup,
        )
        return
    if answer_photo is not None:
        await answer_photo(
            photo=BufferedInputFile(_make_artwork(artwork), filename="mcn-vault.png"),
            caption=text,
            reply_markup=reply_markup,
        )
        return
    await message.answer(text, reply_markup=reply_markup)


def _portal_home_link_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
        ]
    )


def _guardian_activity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏛️ ENTER THE VAULT · +5 ENERGY/ANSWER", callback_data="hub:vault")],
            [InlineKeyboardButton(text="⚔️ UNLIMITED TRIALS · +1 ENERGY/ANSWER", callback_data="hub:trials")],
            [InlineKeyboardButton(text="👤 GUARDIAN PROFILE", callback_data="hub:profile")],
            [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
        ]
    )


async def _send_portal_info(message: types.Message, title: str, body: str, artwork: str = "Guardian Hub"):
    await send_screen(message, f"{title}\n\n{body}", _portal_home_link_keyboard(), artwork)


async def show_kingdom_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "👑 MCN KINGDOM",
        "The Kingdom is the living home of MCN.\n\n"
        "🐾 Enter the Kingdom\n"
        "💎 Discover MCN\n"
        "📊 Track the Token\n"
        "🔐 Verify everything\n"
        "🛡️ Protect the community\n"
        "🏆 Earn rewards\n"
        "📜 Learn the lore\n\n"
        "The path is simple: enter, learn, verify, and become a Guardian.",
        "Guardian Hub",
    )


async def show_oria_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "👁️ ORIA",
        "Oria is the watchful guide of the MCN Kingdom.\n\n"
        "She watches the Guardians, protects the Vault, and calls the Kingdom to truth and discipline.\n\n"
        "Questions Oria can answer:\n"
        "• Who is Oria?\n"
        "• What is the Vault?\n"
        "• What does MCN stand for?\n"
        "• What is a Guardian?\n"
        "• Why Base?\n"
        "• What is the MCN philosophy?",
        "Oria",
    )


async def show_guardians_screen(message: types.Message, user: types.User | None = None):
    await send_screen(
        message,
        "🐾 GUARDIANS\n\n"
        "The MCN Kingdom is built by Guardians who protect, grow, and represent the mission.\n\n"
        "Rank system:\n"
        "🐾 Guardian\n"
        "🛡️ Royal Guardian\n"
        "⭐️ Elite Guardian\n"
        "📜 Ambassador\n"
        "💎 Vault Guardian\n"
        "👑 Legend\n\n"
        "Every Guardian is part of the Kingdom's story and progression.\n\n"
        "Earn Energy by answering questions:\n"
        "🏛️ Daily Vault: 5 questions, +5 Energy for each correct answer.\n"
        "⚔️ Unlimited Trials: keep answering for +1 Energy per correct answer.\n"
        "Your Energy raises your Guardian rank.",
        _guardian_activity_keyboard(),
        "Guardians",
    )


async def show_mcn_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "💎 MCN",
        "MCN is the identity of the Kingdom and the base of its economy and culture.\n\n"
        "MCN is designed to move with utility, community, and long-term trust.\n\n"
        "This portal brings the token story and the Kingdom story together in one place.",
        "mcn kingdom",
    )


async def show_live_data_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "📊 LIVE MCN",
        "💰 Price\n"
        "💧 Liquidity\n"
        "👥 Holders\n"
        "📈 Volume\n"
        "🔄 Transactions\n"
        "🏦 Market Cap\n\n"
        "Important data should be verified on-chain whenever possible for confidence and clarity.",
        "mcn kingdom",
    )


async def show_verify_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "🔐 VERIFY MCN",
        "Official contract:\n0x...\n\n"
        "Network: Base\n"
        "Supply: 1,000,000,000 MCN\n"
        "Tax: 0%\n"
        "Liquidity: 🔒 Locked\n"
        "Ownership: Renounced\n\n"
        "How to buy MCN:\n"
        "1. Get ETH on Base\n"
        "2. Connect your wallet\n"
        "3. Open the official trading link\n"
        "4. Select MCN\n"
        "5. Verify the official contract\n"
        "6. Swap\n\n"
        "Use official links and confirm contract and liquidity before buying.",
        "mcn kingdom",
    )


async def show_security_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "🛡️ STAY SAFE",
        "How to identify the official MCN\n"
        "How to verify the contract\n"
        "Official links\n"
        "Official social accounts\n"
        "How to avoid fake MCN tokens\n"
        "How to avoid fake admins\n\n"
        "Never trust a copycat contract or admin request without verifying official sources.",
        "Guardians",
    )


async def show_rewards_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "🏆 COMMUNITY & REWARDS",
        "🔥 Current contests\n"
        "🎁 Current rewards\n"
        "🏅 Previous winners\n"
        "🎟️ How to participate\n"
        "📜 Contest rules\n\n"
        "Contest flow can include:\n"
        "• registration\n"
        "• wallet check\n"
        "• MCN minimum verification\n"
        "• holding period\n"
        "• participant count\n"
        "• draw and winner publication",
        "mcn kingdom",
    )


async def show_lore_screen(message: types.Message, user: types.User | None = None):
    await _send_portal_info(
        message,
        "📜 THE STORY OF MCN",
        "Chapter I — The Kingdom\n"
        "Chapter II — Oria\n"
        "Chapter III — The Guardians\n"
        "Chapter IV — The Vault\n"
        "Chapter V — The Elite Guardians\n"
        "Chapter VI — Ambassador\n"
        "Chapter VII — Vault Guardian\n"
        "Chapter VIII — Legend\n\n"
        "The lore is the identity of the Kingdom: purpose, trust, guardianship, and growth.",
        "Oria",
    )


async def show_links_screen(message: types.Message, user: types.User | None = None):
    links = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Website", url="https://mainecoonmcn.vercel.app/")],
            [InlineKeyboardButton(text="GeckoTerminal", url="https://www.geckoterminal.com/base/pools/0xc3688a53e99af856fac2a43bd470eb7dd1b0668f")],
            [InlineKeyboardButton(text="DEX Screener", url="https://dexscreener.com/base/0x8e627241838b660cc90f96601952dcd7f47b7831")],
            [InlineKeyboardButton(text="DEXTools", url="https://www.dextools.io/app/base/pair-explorer/0xc3688a53e99af856fac2a43bd470eb7dd1b0668f")],
            [InlineKeyboardButton(text="BaseScan", url="https://basescan.org/token/0x8e627241838b660cc90f96601952dcd7f47b7831")],
            [InlineKeyboardButton(text="Lock Liquidity", url="https://app.uncx.network/lockers/manage/lockers-v3?service=edit&chain=8453&wallet=0x636c3ea0763b55912ad5bf5b2acc6629c9148ee0&locker=0x231278edd38b00b07fbd52120cef685b9baebcc1&pool=0xaa64742981c606881c458e7d5cb8b108e4b60eb8&lock=1156&index=0")],
            *back_keyboard().inline_keyboard,
        ]
    )
    await send_screen(
        message,
        "🌐 OFFICIAL LINKS\n\n"
        "The Kingdom is strongest when its Guardians verify the official sources and the trusted contract information.",
        links,
        "mcn kingdom",
    )


async def send_home(message: types.Message):
    await send_screen(message, HOME_TEXT, home_keyboard(), "Guardian Hub")


@router.message(Command("menu"))
async def open_menu(message: types.Message):
    await send_home(message)


@router.message(Command("verify"))
async def open_verify(message: types.Message):
    await show_verify_screen(message, message.from_user)


@router.message(Command("lore"))
async def open_lore(message: types.Message):
    await show_lore_screen(message, message.from_user)


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
        "kingdom": show_kingdom_screen,
        "oria": show_oria_screen,
        "guardians": show_guardians_screen,
        "mcn": show_mcn_screen,
        "live": show_live_data_screen,
        "verify": show_verify_screen,
        "security": show_security_screen,
        "rewards": show_rewards_screen,
        "lore": show_lore_screen,
        "links": show_links_screen,
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
