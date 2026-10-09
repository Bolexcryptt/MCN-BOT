import asyncio
import csv
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO

import aiosqlite
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from config import MCN_OWNER_ID
from db import (
    ensure_user,
    get_draw_registrations,
    register_draw_wallet,
    update_draw_final_check,
)
from handlers.market_data import (
    MarketDataError,
    fetch_mcn_price_usd,
    fetch_wallet_mcn_balance,
)
from handlers.navigation import back_keyboard, send_screen

router = Router()
logger = logging.getLogger(__name__)
MINIMUM_USD_VALUE = Decimal("10")
WALLET_PATTERN = re.compile(r"0x[0-9a-fA-F]{40}\Z")


class DrawRegisterState(StatesGroup):
    waiting_for_wallet = State()


def _wallet_is_valid(wallet: str) -> bool:
    return bool(WALLET_PATTERN.fullmatch((wallet or "").strip()))


def _is_private(message: types.Message) -> bool:
    return message.chat.type == "private"


def _is_owner(user: types.User | None, chat: types.Chat) -> bool:
    return (
        MCN_OWNER_ID is not None
        and user is not None
        and user.id == MCN_OWNER_ID
        and chat.type == "private"
    )


def _admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 RECHECK ELIGIBILITY", callback_data="drawadmin:recheck")],
            [InlineKeyboardButton(text="📥 EXPORT PARTICIPANTS CSV", callback_data="drawadmin:export")],
            *back_keyboard().inline_keyboard,
        ]
    )


async def show_draw_screen(message: types.Message, user: types.User | None = None):
    if not _is_private(message):
        await message.answer("Please open the bot’s private chat to register for the draw.")
        return
    await ensure_user(user or message.from_user)
    text = (
        "🎟️ DRAW REGISTRATION\n\n"
        "Open to every community member who meets the eligibility rules.\n"
        "Only a public Base wallet address is required.\n"
        "No private key, seed phrase, or wallet password is ever requested.\n\n"
        "Rules:\n"
        "• Hold at least $10 worth of MCN on Base\n"
        "• One wallet = one draw entry\n"
        "• Balance is read from the official MCN contract\n"
        "• MCN/USD price is fetched at registration\n"
        "• Eligibility must be checked again before the draw\n\n"
        "Use the button below to verify your wallet."
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


@router.message(Command("drawtest"))
async def start_draw_test(message: types.Message, state: FSMContext):
    if not _is_private(message):
        await message.answer("Please run /drawtest in the bot’s private chat.")
        return
    await state.set_state(DrawRegisterState.waiting_for_wallet)
    await state.update_data(draw_test_mode=True)
    await message.answer(
        "🧪 PRIVATE CONTEST TEST MODE — OPEN TO ALL\n\n"
        "Send a public Base wallet address to test the live contract balance and MCN/USD price.\n"
        "This test will not create or change a contest registration."
    )


@router.callback_query(F.data == "draw:register")
async def start_draw_registration(callback: types.CallbackQuery, state: FSMContext):
    if not callback.message or not callback.from_user:
        await callback.answer("Draw registration is unavailable.", show_alert=True)
        return
    if not _is_private(callback.message):
        await callback.answer("Open the bot’s private chat to register.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(DrawRegisterState.waiting_for_wallet)
    await callback.message.answer(
        "🎟️ ENTER THE DRAW\n\n"
        "Send your public Base wallet address only.\n"
        "Example: 0x1234567890abcdef1234567890abcdef12345678\n\n"
        "Do not send a private key or seed phrase."
    )


@router.message(DrawRegisterState.waiting_for_wallet, F.text)
async def receive_wallet_for_draw(message: types.Message, state: FSMContext):
    if not _is_private(message):
        await state.clear()
        await message.answer("For your privacy, register only in the bot’s private chat.")
        return

    wallet = (message.text or "").strip()
    if not _wallet_is_valid(wallet):
        await message.answer(
            "❌ Invalid address format. Send a 42-character public Base address "
            "starting with 0x. No wallet secret is required."
        )
        return

    state_data = await state.get_data()
    test_mode = bool(state_data.get("draw_test_mode"))
    try:
        price, price_updated_at = await fetch_mcn_price_usd()
        balance = await fetch_wallet_mcn_balance(wallet)
    except MarketDataError as exc:
        logger.warning("Could not verify draw wallet %s: %s", wallet, exc)
        await message.answer(
            "⚠️ Temporary verification error: Base RPC or the MCN price source is "
            "unavailable right now. Your wallet was not registered. "
            "Please send the same public address again to retry."
        )
        return

    await state.clear()
    usd_value = balance * price
    if test_mode:
        result = "✅ TEST ELIGIBILITY PASS" if usd_value >= MINIMUM_USD_VALUE else "❌ TEST ELIGIBILITY FAIL"
        await message.answer(
            "🧪 PRIVATE CONTEST TEST RESULT\n\n"
            f"Wallet: {wallet}\n"
            f"MCN balance: {balance:,.8f}\n"
            f"Current MCN price: ${price:,.10f}\n"
            f"Estimated value: ${usd_value:,.2f}\n"
            f"Minimum required: ${MINIMUM_USD_VALUE:,.2f}\n"
            f"Price checked: {price_updated_at}\n\n"
            f"{result}\n"
            "No contest entry was created or changed."
        )
        return

    if usd_value < MINIMUM_USD_VALUE:
        await message.answer(
            "❌ INSUFFICIENT MCN BALANCE\n\n"
            f"Wallet: {wallet}\n"
            f"MCN balance: {balance:,.8f}\n"
            f"Current MCN price: ${price:,.10f}\n"
            f"Estimated value: ${usd_value:,.2f}\n"
            f"Minimum required: ${MINIMUM_USD_VALUE:,.2f}\n"
            f"Price checked: {price_updated_at}\n\n"
            "This wallet has not been registered."
        )
        return

    try:
        registered = await register_draw_wallet(
            user_id=message.from_user.id,
            wallet_address=wallet,
            registration_mcn_qty=str(balance),
            registration_usd_value=float(usd_value),
            registration_price=float(price),
        )
    except aiosqlite.Error:
        logger.exception("Could not save draw registration for wallet %s", wallet)
        await message.answer(
            "⚠️ Verification passed, but the registration could not be saved. "
            "Please try again; no entry was confirmed."
        )
        return

    if not registered:
        await message.answer(
            "ℹ️ This wallet already has a draw entry. One wallet can only be "
            "registered once."
        )
        return

    await message.answer(
        "🎟️ DRAW REGISTRATION\n\n"
        f"Wallet: {wallet}\n"
        f"MCN balance: {balance:,.8f}\n"
        f"Current MCN price: ${price:,.10f}\n"
        f"Estimated value: ${usd_value:,.2f}\n"
        f"Minimum required: ${MINIMUM_USD_VALUE:,.2f}\n"
        f"Price checked: {price_updated_at}\n\n"
        "✅ Eligible — this wallet is registered. It will be checked again before the draw."
    )


@router.message(Command("drawadmin"))
async def open_draw_admin(message: types.Message):
    if not _is_private(message):
        return
    if not _is_owner(message.from_user, message.chat):
        await message.answer("⛔ This private admin command is not available.")
        return
    await _send_participant_list(message)


def _registration_row(row: tuple) -> str:
    _, wallet, registered_at, quantity, usd_value, price, eligible, checked, checked_at, final_qty, final_usd, *rest = row
    if rest and rest[0] == "error":
        final_status = "⚠️ Recheck error"
    elif checked_at is None:
        final_status = "⏳ Not checked"
    else:
        final_status = "✅ Passed" if checked else "❌ Failed"
    return (
        f"{wallet}\n"
        f"  Registered: {registered_at}\n"
        f"  Registered balance/value: {quantity or 'n/a'} MCN / "
        f"${(usd_value or 0):,.2f} (price ${price or 0:,.10f})\n"
        f"  Registration eligibility: {'✅ Eligible' if eligible else '❌ Ineligible'}\n"
        f"  Final check: {final_status}"
        + (
            f" — {final_qty or 'n/a'} MCN / ${final_usd:,.2f}"
            if final_usd is not None
            else ""
        )
    )


async def _send_participant_list(message: types.Message):
    participants = await get_draw_registrations()
    await message.answer(f"🔐 PRIVATE DRAW ADMIN\nRegistered participants: {len(participants)}")
    if not participants:
        await message.answer("No participants are registered yet.", reply_markup=_admin_keyboard())
        return

    chunks: list[str] = []
    current = "🎟️ REGISTERED PARTICIPANTS\n\n"
    for index, row in enumerate(participants, 1):
        entry = f"{index}. {_registration_row(row)}\n\n"
        if len(current) + len(entry) > 3500 and current.strip():
            chunks.append(current)
            current = ""
        current += entry
    if current.strip():
        chunks.append(current)
    for chunk in chunks:
        await message.answer(chunk)
    await message.answer("Admin actions:", reply_markup=_admin_keyboard())


def _make_participants_csv(participants: list[tuple]) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        (
            "wallet_address",
            "registration_mcn_balance",
            "registration_usd_value",
            "registration_price_usd",
            "registration_eligibility",
            "registered_at_utc",
            "final_check_status",
            "final_mcn_balance",
            "final_usd_value",
            "final_checked_at_utc",
        )
    )
    for row in participants:
        (
            _user_id,
            wallet,
            registered_at,
            quantity,
            usd_value,
            price,
            eligible,
            final_passed,
            final_checked_at,
            final_qty,
            final_usd,
            *rest,
        ) = row
        final_status = rest[0] if rest else None
        if final_status is None:
            if final_checked_at is None:
                final_status = "not_checked"
            else:
                final_status = "passed" if final_passed else "failed"
        writer.writerow(
            (
                wallet,
                quantity,
                usd_value,
                price,
                "eligible" if eligible else "ineligible",
                registered_at,
                final_status,
                final_qty,
                final_usd,
                final_checked_at,
            )
        )
    return output.getvalue().encode("utf-8-sig")


@router.callback_query(F.data.startswith("drawadmin:"))
async def draw_admin_action(callback: types.CallbackQuery):
    if not callback.message or not _is_owner(callback.from_user, callback.message.chat):
        await callback.answer("⛔ Admin access denied.", show_alert=True)
        return

    action = callback.data.partition(":")[2] if callback.data else ""
    if action == "export":
        participants = await get_draw_registrations()
        file = BufferedInputFile(
            _make_participants_csv(participants),
            filename="mcn_draw_participants.csv",
        )
        await callback.answer()
        await callback.message.answer_document(
            file,
            caption=f"Private export: {len(participants)} registered participant(s).",
        )
        return

    if action == "recheck":
        await callback.answer("Checking participants against Base and current price…")
        await _recheck_eligibility(callback.message)
        return

    await callback.answer("Unknown admin action.", show_alert=True)


async def _recheck_eligibility(message: types.Message):
    participants = await get_draw_registrations()
    if not participants:
        await message.answer("There are no registered wallets to recheck.")
        return

    try:
        price, checked_at = await fetch_mcn_price_usd()
    except MarketDataError as exc:
        logger.warning("Could not recheck draw eligibility: %s", exc)
        await message.answer(
            "⚠️ Temporary verification error: the current MCN/USD price is "
            "unavailable. No eligibility statuses were changed."
        )
        return

    semaphore = asyncio.Semaphore(4)

    async def check_one(row: tuple):
        wallet = row[1]
        async with semaphore:
            try:
                balance = await fetch_wallet_mcn_balance(wallet)
            except MarketDataError as exc:
                logger.warning("Could not recheck draw wallet %s: %s", wallet, exc)
                await update_draw_final_check(
                    wallet, None, "error", checked_at, None, None
                )
                return wallet, "⚠️ RPC error; eligibility unknown"

        value = balance * price
        passed = value >= MINIMUM_USD_VALUE
        await update_draw_final_check(
            wallet,
            passed,
            "passed" if passed else "failed",
            checked_at,
            str(balance),
            float(value),
        )
        status = "✅ eligible" if passed else "❌ no longer eligible"
        return wallet, f"{status} — {balance:,.6f} MCN (${value:,.2f})"

    results = await asyncio.gather(*(check_one(row) for row in participants))
    header = (
        "🔄 FINAL ELIGIBILITY RECHECK\n\n"
        f"MCN price: ${price:,.10f}\n"
        f"Checked: {checked_at}\n\n"
    )
    chunks: list[str] = []
    current = header
    for index, (wallet, status) in enumerate(results, 1):
        line = f"{index}. {wallet}: {status}\n"
        if len(current) + len(line) > 3500 and current.strip():
            chunks.append(current)
            current = ""
        current += line
    current += (
        "\nOnly ✅ eligible wallets currently meet the $10 threshold. "
        "⚠️ RPC errors remain unknown and must be rechecked."
    )
    chunks.append(current)
    for index, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            reply_markup=_admin_keyboard() if index == len(chunks) - 1 else None,
        )
