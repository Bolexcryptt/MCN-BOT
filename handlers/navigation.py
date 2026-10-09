
import logging
from io import BytesIO
from pathlib import Path

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont

from handlers.market_data import (
    MarketDataError,
    fetch_contract_facts,
    fetch_live_metrics,
)

router = Router()
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = PROJECT_ROOT

_ARTWORK_ASSET_MAP = {
    "rank vault guardian": ("vault2.png", "thevault.png"),
    "rank royal guardian": ("royalguardians.png",),
    "rank elite guardian": ("eliteguardians.png",),
    "rank ambassador": ("ambassador.png",),
    "rank guardian": ("guardians.png",),
    "rank legend": ("kingdom3.png", "kingdom4.png"),
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
    "royal guardian": ("royalguardians.png", "kingdom4.png"),
    "elite guardian": ("eliteguardians.png", "kingdom3.png"),
    "ambassador": ("ambassador.png", "royalguardians.png", "mcnlogo.png"),
    "mcn question": ("mcntoken.png", "mcnlogo.png", "kingdom3.png"),
    "base question": ("kingdom4.png", "mcnlogo.png", "mcntoken.png"),
    "daily guardian activity": ("kingdom3.png", "kingdom4.png", "kingdom2.png"),
    "guardian recruitment": ("mcnlogo.png", "mcntoken.png", "ambassador.png"),
    "mcn kingdom": ("mcnlogo.png", "mcntoken.png", "ambassador.png"),
    "oria": ("oria.png", "kingdom3.png", "kingdom4.png"),
    "guardians": ("guardians.png", "eliteguardians.png", "royalguardians.png"),
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

HOLD_CONTEST_TEXT = (
    "🐾 The MCN Hold Contest is back.\n\n"
    "Hold at least $10 of MCN on Base and you’re in.\n\n"
    "5 winners will be selected every week.\n"
    "Each winner receives $5 worth of ETH.\n\n"
    "1️⃣ Follow @MCN_MAINECOON\n"
    "2️⃣ Follow @KingStanny\n"
    "3️⃣ Buy & hold at least $10 of $MCN\n\n"
    "The Vault is open.\n"
    "Oria is watching. 👀"
)

ACTIVE_CONTEST_TEXT: str | None = HOLD_CONTEST_TEXT

LIQUIDITY_LOCK_TEXT = "Withdrawal becomes available after August 10, 2027, 6:53 PM UTC."

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
            [InlineKeyboardButton(text="👑 RANKS & LEADERBOARD", callback_data="hub:leaderboard")],
            [InlineKeyboardButton(text="🔔 NOTIFICATIONS & UPDATES", callback_data="hub:notifications")],
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
            [InlineKeyboardButton(text="🌐 OFFICIAL LINKS", callback_data="hub:links")],
            [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
        ]
    )


def _guardian_activity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏛️ ENTER THE VAULT · +5 ENERGY/ANSWER", callback_data="hub:vault")],
            [InlineKeyboardButton(text="⚔️ UNLIMITED TRIALS · +1 ENERGY/ANSWER", callback_data="hub:trials")],
            [InlineKeyboardButton(text="👑 RANKS & LEADERBOARD", callback_data="hub:leaderboard")],
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
    await send_screen(
        message,
        "💎 MCN\n\n"
        "MCN is the identity of the Kingdom and the base of its economy and culture.\n\n"
        "MCN is designed to move with utility, community, and long-term trust.\n\n"
        "This portal brings the token story and the Kingdom story together in one place.",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Visit the MCN Website", url="https://mainecoonmcn.vercel.app/")],
                [InlineKeyboardButton(text="🔐 Verify MCN", callback_data="hub:verify")],
                [InlineKeyboardButton(text="🌐 All Official Links", callback_data="hub:links")],
                [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
            ]
        ),
        "mcn kingdom",
    )


async def show_draw_screen(message: types.Message, user: types.User | None = None):
    from handlers.draw import show_draw_screen as draw_entry

    await draw_entry(message, user)


def _live_data_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Price", callback_data="live:price"),
                InlineKeyboardButton(text="💧 Liquidity", callback_data="live:liquidity"),
            ],
            [
                InlineKeyboardButton(text="👥 Holders", callback_data="live:holders"),
                InlineKeyboardButton(text="📈 Volume", callback_data="live:volume"),
            ],
            [
                InlineKeyboardButton(text="🔄 Transactions", callback_data="live:transactions"),
                InlineKeyboardButton(text="🏦 Market Cap", callback_data="live:market_cap"),
            ],
            [InlineKeyboardButton(text="🔄 Refresh all", callback_data="live:all")],
            [InlineKeyboardButton(
                text="🔎 Holders on BaseScan",
                url="https://basescan.org/token/0x8e627241838b660cc90f96601952dcd7f47b7831#balances",
            )],
            [InlineKeyboardButton(text="🌐 Official Links", callback_data="hub:links")],
            *back_keyboard().inline_keyboard,
        ]
    )


async def show_live_data_screen(
    message: types.Message,
    user: types.User | None = None,
    metric: str = "all",
):
    try:
        data = await fetch_live_metrics()
    except MarketDataError as exc:
        logger.warning("Could not load live MCN market data: %s", exc)
        text = (
            "📊 LIVE MCN\n\n"
            "Live MCN data is temporarily unavailable from GeckoTerminal.\n"
            "Please try Refresh all again shortly.\n\n"
            f"Last request: {exc}"
        )
        await send_screen(message, text, _live_data_keyboard(), "mcn kingdom")
        return

    metrics = (
        ("💰 Price", "price"),
        ("💧 Liquidity", "liquidity"),
        ("👥 Holders", "holders"),
        ("📈 24h Volume", "volume"),
        ("🔄 24h Transactions", "transactions"),
        ("🏦 Market Cap", "market_cap"),
    )
    if metric == "all":
        values = "\n".join(f"{label}: {data[key]}" for label, key in metrics)
        values += f"\n📐 Fully diluted valuation (FDV): {data['fdv']}"
        title = "📊 LIVE MCN · BASE"
    else:
        selected = next(((label, key) for label, key in metrics if key == metric), None)
        if selected is None:
            await send_screen(
                message,
                "⚠️ That live-data metric is not available.",
                _live_data_keyboard(),
                "mcn kingdom",
            )
            return
        label, key = selected
        values = f"{label}: {data[key]}"
        if key == "market_cap":
            values += f"\nFDV (not market cap): {data['fdv']}"
        title = f"📊 LIVE MCN · {label.upper()}"

    await send_screen(
        message,
        f"{title}\n\n{values}\n\n"
        f"🕒 Last updated: {data['updated_at']}\n"
        "Source: GeckoTerminal pool data (indexed market data, not a direct chain read).\n"
        "Holder count and market cap are not provided by this pool endpoint; they are not estimated.",
        _live_data_keyboard(),
        "mcn kingdom",
    )


@router.callback_query(F.data.startswith("live:"))
async def show_live_data_metric(callback: types.CallbackQuery):
    if not callback.message or not callback.data:
        await callback.answer("Live MCN data is unavailable.", show_alert=True)
        return
    metric = callback.data.partition(":")[2]
    await callback.answer()
    await show_live_data_screen(callback.message, callback.from_user, metric)


async def show_verify_screen(message: types.Message, user: types.User | None = None):
    try:
        contract_facts = await fetch_contract_facts()
        supply_line = (
            f"Total supply: {contract_facts['supply']} MCN "
            "(verified via Base totalSupply())"
        )
        ownership_line = (
            f"Ownership: {contract_facts['ownership']} "
            "(verified via Base owner())"
        )
        contract_checked_at = contract_facts["updated_at"]
    except MarketDataError as exc:
        logger.warning("Could not read MCN contract facts from Base: %s", exc)
        supply_line = "Total supply: unavailable from current Base RPC read"
        ownership_line = "Ownership: unavailable from current Base RPC read"
        contract_checked_at = "Base contract read unavailable"

    verify_links = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔎 Verify token on BaseScan",
                url="https://basescan.org/token/0x8e627241838b660cc90f96601952dcd7f47b7831",
            )],
            [InlineKeyboardButton(
                text="🔒 Check liquidity lock",
                url="https://app.uncx.network/lockers/manage/lockers-v3?service=edit&chain=8453&wallet=0x636c3ea0763b55912ad5bf5b2acc6629c9148ee0&locker=0x231278edd38b00b07fbd52120cef685b9baebcc1&pool=0xaa64742981c606881c458e7d5cb8b108e4b60eb8&lock=1156&index=0",
            )],
            *back_keyboard().inline_keyboard,
        ]
    )
    await send_screen(
        message,
        "🔐 VERIFY MCN\n\n"
        "Official contract:\n0x8e627241838b660cc90f96601952dcd7f47b7831\n\n"
        "Network: Base\n"
        f"{supply_line}\n"
        f"{ownership_line}\n"
        f"Contract read updated: {contract_checked_at}\n\n"
        "Project-stated (not automatically verified by this screen): 0% tax; no presale; no team tokens; no mint; no blacklist; no pause function.\n"
        f"Liquidity lock record (UNCX): {LIQUIDITY_LOCK_TEXT}\n\n"
        "Open the linked BaseScan and UNCX records to independently inspect current contract and lock details.\n\n"
        "How to buy MCN:\n"
        "1. Get ETH on Base\n"
        "2. Connect your wallet\n"
        "3. Open the official trading link\n"
        "4. Select MCN\n"
        "5. Verify the official contract\n"
        "6. Swap\n\n"
        "Use official links and confirm contract and liquidity before buying.",
        verify_links,
        "mcn kingdom",
    )


async def show_security_screen(message: types.Message, user: types.User | None = None):
    await send_screen(
        message,
        "🛡️ STAY SAFE\n\n"
        "Never share:\n"
        "• Seed phrases\n"
        "• Private keys\n"
        "• Wallet passwords\n"
        "MCN will never ask for your private keys.\n\n"
        "How to identify official MCN:\n"
        "• Start from the MCN website and use its official links.\n"
        "• Confirm the token address on BaseScan: 0x8e627241838b660cc90f96601952dcd7f47b7831.\n"
        "• Check the network is Base and compare addresses character by character.\n"
        "• Verify the liquidity locker through the official locker record.\n"
        "• MetaMask is a wallet for interacting with Base, not a token listing.\n\n"
        "Avoid fake tokens and admins:\n"
        "• Never trust a token name, logo, unsolicited DM or search result alone.\n"
        "• Never send funds to an admin to prove your wallet.\n"
        "• Ignore urgent investment promises; verify through official community links.\n\n"
        "Always verify the official contract, official links, and Base network.\n"
        "When in doubt, verify before interacting.",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Visit MCN Website", url="https://mainecoonmcn.vercel.app/")],
                [InlineKeyboardButton(text="🔐 Verify Contract", callback_data="hub:verify")],
                [InlineKeyboardButton(text="🌐 Official Links", callback_data="hub:links")],
                [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
            ]
        ),
        "Guardians",
    )


async def show_rewards_screen(message: types.Message, user: types.User | None = None):
    contest_text = f"🔥 CURRENT CONTEST\n\n{ACTIVE_CONTEST_TEXT}" if ACTIVE_CONTEST_TEXT else (
        "There is currently no active contest.\n"
        "There is no current contest reward."
    )
    winner_text = (
        "🏅 Previous winners: check official project announcements; "
        "no winner list is published in this bot yet."
    )
    participation_text = (
        "🎟️ How to participate and 📜 contest rules are included in the active announcement."
        if ACTIVE_CONTEST_TEXT
        else "Follow official MCN announcements for future contest rules."
    )
    contest_details = (
        f"{contest_text}\n\n"
        + (
            "🎁 Current reward: each weekly winner receives $5 worth of ETH.\n"
            if ACTIVE_CONTEST_TEXT
            else ""
        )
        + f"{winner_text}\n{participation_text}\n\n"
    )
    await send_screen(
        message,
        "🏆 COMMUNITY & REWARDS\n\n" + contest_details
        + "Never share wallet credentials or private keys.",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎟️ ENTER THE DRAW", callback_data="draw:register")],
                [InlineKeyboardButton(text="👑 RANKS & LEADERBOARD", callback_data="hub:leaderboard")],
                [InlineKeyboardButton(text="🎖️ GUARDIAN PROFILE", callback_data="hub:profile")],
                [InlineKeyboardButton(text="🧲 INVITE A GUARDIAN", callback_data="hub:invite")],
                [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
            ]
        ),
        "mcn kingdom",
    )


async def show_notifications_screen(message: types.Message, user: types.User | None = None):
    update_text = ACTIVE_CONTEST_TEXT or "There is currently no active contest."
    await send_screen(
        message,
        "🔔 MCN NOTIFICATIONS & PROJECT UPDATES\n\n"
        + update_text
        + "\n\nFollow the official MCN channels for future announcements.",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🐾 @MCN_MAINECOON", url="https://x.com/MCN_MAINECOON")],
                [InlineKeyboardButton(text="👑 @KingStanny", url="https://x.com/KingStanny")],
                [InlineKeyboardButton(text="🌐 MCN Website", url="https://mainecoonmcn.vercel.app/")],
                [InlineKeyboardButton(text="🏆 COMMUNITY & REWARDS", callback_data="hub:rewards")],
                [InlineKeyboardButton(text="🏠 KINGDOM HOME", callback_data="navigation:home")],
            ]
        ),
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
            [InlineKeyboardButton(text="🛡️ Anti-scam safety", callback_data="hub:security")],
            [InlineKeyboardButton(text="🔐 Verify MCN", callback_data="hub:verify")],
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


@router.message(Command("links"))
async def open_links(message: types.Message):
    await show_links_screen(message, message.from_user)


@router.message(Command("security"))
async def open_security(message: types.Message):
    await show_security_screen(message, message.from_user)


@router.message(Command("buy"))
async def open_buy_guide(message: types.Message):
    await show_verify_screen(message, message.from_user)


@router.message(Command("notifications"))
async def open_notifications(message: types.Message):
    await show_notifications_screen(message, message.from_user)


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
        "notifications": show_notifications_screen,
        "lore": show_lore_screen,
        "links": show_links_screen,
        "vault": vault.show_vault,
        "trials": vault.show_trials,
        "profile": profile.show_profile,
        "leaderboard": leaderboard.show_leaderboard,
        "invite": invite.show_invite,
        "daily": vault.show_daily,
        "draw": show_draw_screen,
    }
    handler = handlers.get(section)
    if handler is None:
        await callback.answer("Unknown Guardian Hub action.", show_alert=True)
        return

    await callback.answer()
    await handler(callback.message, callback.from_user)
