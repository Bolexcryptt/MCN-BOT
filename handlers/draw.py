import re
from decimal import Decimal, InvalidOperation

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db import ensure_user, upsert_draw_registration
from handlers.market_data import fetch_live_metrics, fetch_wallet_mcn_balance
from handlers.navigation import back_keyboard, send_screen

router = Router()


class DrawRegisterState(StatesGroup):
    waiting_for_wallet = State()


def _wallet_is_valid(wallet: str) -> bool:
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", (wallet or "").strip()))


async def show_draw_screen(message: types.Message, user: types.User | None = None):
    await ensure_user(user or message.from_user)
    text = (
        "🎟️ DRAW REGISTRATION\n\n"
        "Only a public Base wallet address is required.\n"
        "No private key, no seed phrase, no wallet secret is ever requested.\n\n"
        "Rules:\n"
        "• Must hold at least $10 worth of MCN on Base\n"
        "• One wallet = one draw entry\n"
        "• Verification happens on-chain at the time of registration\n"
        "• Final eligibility is checked again before the draw\n\n"
        "Click below to start wallet verification."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟️ REGISTER MY WALLET", callback_data="draw:register")],
            *back_keyboard().inline_keyboard,
        ]
    )
    await send_screen(message, text, keyboard, "mcn kingdom")


@router.message(Command("draw"))
async def open_draw(message: types.Message):
    await show_draw_screen(message, message.from_user)


@router.callback_query(F.data == "draw:register")
async def start_draw_registration(callback: types.CallbackQuery, state: FSMContext):
    if not callback.message or not callback.from_user:
        await callback.answer("Draw registration is unavailable.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(DrawRegisterState.waiting_for_wallet)
    await callback.message.answer(
        "🎟️ ENTER THE DRAW\n\n"
        "Send your public Base wallet address only.\n"
        "Example: 0x1234567890abcdef1234567890abcdef12345678\n\n"
        "The bot will check your MCN balance and compare it to the current $10 threshold."
    )


@router.message(DrawRegisterState.waiting_for_wallet, F.text)
async def receive_wallet_for_draw(message: types.Message, state: FSMContext):
    wallet = (message.text or "").strip()
    if not _wallet_is_valid(wallet):
        await message.answer(
            "❌ That wallet address is invalid.\n\n"
            "Please send a public Base wallet in this format:\n"
            "0x1234567890abcdef1234567890abcdef12345678\n\n"
            "No private keys or seed phrases are ever required."
        )
        return

    await state.clear()
    try:
        price_data = await fetch_live_metrics()
        price_text = price_data.get("price", "Unavailable")
        try:
            price_value = Decimal(str(price_text).replace("$", "").replace(",", ""))
        except (InvalidOperation, ValueError):
            price_value = Decimal("0")

        balance = await fetch_wallet_mcn_balance(wallet)
        usd_value = balance * price_value
        minimum_required = Decimal("10")
        eligible = usd_value >= minimum_required

        regulatory_text = (
            "✅ Eligible — wallet added to the draw."
            if eligible
            else "❌ Ineligible — wallet does not meet the $10 MCN minimum."
        )
        details = (
            "🎟️ DRAW REGISTRATION\n\n"
            f"Wallet: {wallet}\n"
            f"MCN balance: {balance:,.6f}\n"
            f"Current value: ${usd_value:,.2f}\n"
            f"Minimum required: ${minimum_required:,.2f}\n\n"
            f"{regulatory_text}"
        )

        await upsert_draw_registration(
            user_id=message.from_user.id,
            wallet_address=wallet,
            registration_mcn_qty=str(balance),
            registration_usd_value=float(usd_value),
            registration_price=float(price_value),
            eligible_for_draw=int(bool(eligible)),
        )

        await message.answer(details)
        await message.answer(
            "🕒 Final eligibility checks happen again before the draw.\n"
            "Bots can verify balances on-chain, but the final winner list remains under project review."
        )
    except Exception as exc:  # pragma: no cover - defensive guard for public on-chain checks
        await message.answer(
            "⚠️ The bot could not verify the wallet right now.\n"
            "Please try again in a moment and confirm the public Base address is correct."
        )
        raise exc


@router.message(F.text)
async def draw_guard_for_unrelated_text(message: types.Message):
    if message.text and message.text.strip().startswith("0x") and len(message.text.strip()) >= 42:
        await receive_wallet_for_draw(message, FSMContext(storage=None))
