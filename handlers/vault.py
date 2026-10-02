import random
import secrets
from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db import (
    add_points,
    award_vault_answer,
    claim_daily,
    complete_daily_challenge,
    ensure_user,
    get_user,
    save_vault_state,
    start_daily_challenge,
)
from handlers.navigation import back_keyboard, send_screen

router = Router()

QUESTIONS = [
    ("What is 2 + 2?", "4"),
    ("What is 5 + 3?", "8"),
    ("What is 10 - 4?", "6"),
    ("What is the name of our guardian leader?", "oria"),
    ("Who is always watching the system?", "oria"),
    ("Who guides the guardians?", "oria"),
    ("What protects the MCN ecosystem?", "the vault"),
    ("What is the central system of MCN?", "the vault"),
    ("What must guardians protect?", "the vault"),
    ("Who are the community members?", "guardians"),
    ("What do we call active members?", "guardians"),
    ("Who protects and builds?", "guardians"),
    ("What is our growth style?", "organic"),
    ("How does MCN grow?", "organic"),
    ("Where are we building?", "base"),
    ("What chain are we focused on?", "base"),
    ("What do Guardians do?", "protect and build"),
    ("What is a Guardian's duty?", "protect and build"),
    ("What happens when you earn points?", "the vault grows"),
    ("What does energy do?", "strengthens the vault"),
    ("What is the highest rank?", "ambassador"),
    ("Who represents MCN externally?", "ambassador"),
    ("What rank comes after Guardian?", "elite guardian"),
    ("What rank comes after Elite Guardian?", "royal guardian"),
    ("What does Oria observe?", "guardians"),
    ("Who is rising in the system?", "guardians"),
    ("What must you do during Vault attacks?", "defend"),
    ("What word protects the vault?", "defend"),
    ("What is rewarded in trials?", "energy"),
    ("What do you gain from activity?", "energy"),
]

vault_users: dict[int, int] = {}
question_users: dict[int, bool] = {}
current_answers: dict[int, str] = {}
current_tokens: dict[int, str] = {}
user_points: dict[int, int] = {}
last_vault: dict[int, object] = {}
TOTAL_VAULT_QUESTIONS = 5


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _category(question: str, answer: str) -> str:
    prompt = question.casefold()
    if "oria" in prompt or "watch" in prompt or "observe" in prompt:
        return "👁️ Oria's Trial"
    if any(word in prompt for word in ("protect", "defend", "vault", "guardian")):
        return "🛡️ Defense Trial"
    if any(character.isdigit() for character in prompt):
        return "⚡ Speed Trial"
    if answer in {"energy", "base", "organic"}:
        return "🧠 Knowledge Trial"
    return "🧠 Knowledge Trial"


def _answer_options(answer: str) -> list[str]:
    wrong_answers = list(dict.fromkeys(item[1] for item in QUESTIONS if item[1] != answer))
    options = [answer, random.choice(wrong_answers)]
    random.shuffle(options)
    return options


def build_answer_keyboard(
    user_id: int,
    options: list[str],
    token: str = "manual",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=f"answer:{user_id}:{token}:{option}",
            )]
            for option in options
        ] + [[InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")]]
    )


def _daily_keyboard(user_id: int, today: str, answer: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=f"dailyanswer:{user_id}:{today}:{option}",
            )]
            for option in _answer_options(answer)
        ] + [[InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")]]
    )


def _daily_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ CLAIM DAILY ENERGY", callback_data="daily:claim")],
            [InlineKeyboardButton(text="🧠 DAILY CHALLENGE", callback_data="daily:challenge")],
            *back_keyboard().inline_keyboard,
        ]
    )


def clear_user_session(user_id: int):
    vault_users.pop(user_id, None)
    last_vault.pop(user_id, None)
    question_users.pop(user_id, None)
    current_answers.pop(user_id, None)
    current_tokens.pop(user_id, None)


async def handle_answer_for_user(
    user_id: int,
    user: types.User,
    message: types.Message,
    answer: str,
):
    if user_id not in current_answers:
        return

    correct = current_answers[user_id]
    if user_id in vault_users:
        if answer == correct:
            progress = vault_users[user_id]
            awarded, energy = await award_vault_answer(user_id, progress, _today())
            if not awarded:
                current_answers.pop(user_id, None)
                current_tokens.pop(user_id, None)
                await send_screen(
                    message,
                    "⚠️ This Vault answer was already recorded, or today's trial is no longer active.",
                    back_keyboard(),
                    "Vault Signal",
                )
                return

            progress += 1
            vault_users[user_id] = progress
            user_points[user_id] = energy
            current_answers.pop(user_id, None)
            current_tokens.pop(user_id, None)
            if progress >= TOTAL_VAULT_QUESTIONS:
                await save_vault_state(user_id, _today(), progress, None, None)
                vault_users.pop(user_id, None)
                await send_screen(
                    message,
                    "🟦 VAULT TRIAL COMPLETE\n\n"
                    "✨ The seal opens. You have proven your resolve.\n\n"
                    "🛡️ +5 Energy earned on each correct answer\n"
                    f"⚡ Total Energy: {energy:,}\n"
                    "🏛️ Vaults completed: +1\n\n"
                    "👁️ Oria has witnessed your defense. Return tomorrow for another trial.",
                    back_keyboard(),
                    "Vault Trial Complete",
                )
                return

            await send_screen(
                message,
                "✅ SEAL STABILIZED\n\n"
                f"⚡ +5 Energy  •  Total: {energy:,}\n"
                f"🛡️ Vault progress: {progress}/{TOTAL_VAULT_QUESTIONS}\n\n"
                "👁️ Oria watches the next chamber...",
                artwork="Vault Trial",
            )
            await send_vault_question(message, user_id, persist=True)
            return

        current_answers.pop(user_id, None)
        current_tokens.pop(user_id, None)
        await send_screen(
            message,
            "❌ THE SEAL HOLDS\n\n"
            "That answer did not pass Oria's test. Your progress is safe, Guardian.\n"
            "Focus, steady your energy, and face the next signal.",
            artwork="Vault Trial",
        )
        await send_vault_question(message, user_id, persist=True)
        return

    if user_id in question_users:
        if answer == correct:
            await add_points(user, 1)
            data = await get_user(user_id)
            energy = data[2] if data else 0
            user_points[user_id] = energy
            current_answers.pop(user_id, None)
            current_tokens.pop(user_id, None)
            await send_screen(
                message,
                f"✅ TRIAL PASSED\n\n⚡ +1 Energy  •  Total: {energy:,}\n"
                "Oria records your progress.",
                artwork="Guardian Trial",
            )
            await send_question(message, user_id)
            return

        current_answers.pop(user_id, None)
        current_tokens.pop(user_id, None)
        await send_screen(
            message,
            "❌ TRIAL FAILED\n\n"
            "The answer was not accepted. Regroup, Guardian — your next trial is ready.",
            artwork="Guardian Trial",
        )
        await send_question(message, user_id)


@router.callback_query(F.data.startswith("answer:"))
async def handle_button_answer(callback: types.CallbackQuery):
    if not callback.message or not callback.data:
        return

    try:
        _, user_id_str, token, answer = callback.data.split(":", 3)
        user_id = int(user_id_str)
        selected_answer = answer.strip().casefold()
    except (ValueError, TypeError):
        await callback.answer("Invalid answer.", show_alert=True)
        return

    if (
        callback.from_user.id != user_id
        or user_id not in current_answers
        or current_tokens.get(user_id) != token
    ):
        await callback.answer("This question is no longer active.", show_alert=True)
        return

    await callback.answer()
    await handle_answer_for_user(user_id, callback.from_user, callback.message, selected_answer)


@router.message(Command("vault"))
async def start_vault(msg: types.Message):
    await show_vault(msg, msg.from_user)


async def show_vault(message: types.Message, user: types.User):
    await ensure_user(user)
    user_id = user.id
    today = _today()
    data = await get_user(user_id)
    guardian_rank = data[8] if data and len(data) > 8 else "Initiate"
    if data and data[10] == today:
        progress = data[11] or 0
        if progress >= TOTAL_VAULT_QUESTIONS:
            await send_screen(
                message,
                "⚠️ TODAY'S VAULT IS SEALED\n\n"
                "You have completed today's five-question Guardian Trial.\n"
                "Return tomorrow, Guardian. Oria is always watching.",
                back_keyboard(),
                "Vault Access",
            )
            return
        vault_users[user_id] = progress
        last_vault[user_id] = today
        question, answer = data[12], data[13]
        if question and answer:
            await send_screen(
                message,
                "🟦 VAULT CONNECTION RESTORED\n\n"
                f"👁️ Oria preserved your trial at {progress + 1}/{TOTAL_VAULT_QUESTIONS}.",
                artwork="Vault Entrance",
            )
            await _send_question(message, user_id, question, answer, progress, vault=True)
            return
        await send_screen(
            message,
            "🟦 VAULT CONNECTION RESTORED\n\n"
            f"👁️ Oria preserved your trial at {progress}/{TOTAL_VAULT_QUESTIONS}.\n"
            "Your next seal is ready.",
            artwork="Vault Entrance",
        )
        await send_vault_question(message, user_id, persist=True)
        return
    else:
        vault_users[user_id] = 0
        last_vault[user_id] = today
        await save_vault_state(user_id, today, 0, None, None)

    await send_screen(
        message,
        "🟦 THE VAULT\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👁️ Oria is watching...\n\n"
        f"🛡️ {guardian_rank} Trial\n"
        "⚡ Energy at stake: +5 per correct seal\n"
        f"🏛️ Trial status: {vault_users[user_id]}/{TOTAL_VAULT_QUESTIONS}\n\n"
        "Five questions stand between you and completion. Your daily attempt begins now.",
        artwork="Vault Entrance",
    )
    await send_vault_question(message, user_id, persist=True)


async def send_vault_question(
    msg: types.Message,
    user_id: int | None = None,
    persist: bool = False,
):
    user_id = user_id or msg.from_user.id
    question, answer = random.choice(QUESTIONS)
    progress = vault_users.get(user_id, 0)
    await _send_question(msg, user_id, question, answer, progress, vault=True, persist=persist)


async def _send_question(
    message: types.Message,
    user_id: int,
    question: str,
    answer: str,
    progress: int,
    vault: bool,
    persist: bool = False,
):
    answer = answer.casefold()
    current_answers[user_id] = answer
    token = secrets.token_hex(3)
    current_tokens[user_id] = token
    if persist and vault:
        await save_vault_state(user_id, _today(), progress, question, answer)

    if vault:
        text = (
            "🟦 THE VAULT  •  GUARDIAN TRIAL\n\n"
            f"👁️ Oria is watching  |  Seal {progress + 1}/{TOTAL_VAULT_QUESTIONS}\n\n"
            f"{question}\n\n"
            "Choose your response. Your progress is preserved."
        )
        artwork = "Vault Trial"
    else:
        text = f"{_category(question, answer)}\n\n👁️ Oria is watching.\n\n{question}"
        artwork = "Guardian Trial"

    await send_screen(
        message,
        text,
        build_answer_keyboard(user_id, _answer_options(answer), token),
        artwork,
    )


@router.message(Command("questions"))
async def start_questions(msg: types.Message):
    await show_trials(msg, msg.from_user)


async def show_trials(message: types.Message, user: types.User):
    await ensure_user(user)
    user_id = user.id
    vault_users.pop(user_id, None)
    current_tokens.pop(user_id, None)
    question_users[user_id] = True
    await send_screen(
        message,
        "⚡ UNLIMITED GUARDIAN TRIALS\n\n"
        "Choose a signal and test your knowledge.\n"
        "🧠 Knowledge  •  🛡️ Defense  •  ⚡ Speed  •  👁️ Oria's Trial\n\n"
        "Correct answers earn +1 Energy. There is no daily limit.",
        artwork="Guardian Trials",
    )
    await send_question(message, user_id)


async def send_question(msg: types.Message, user_id: int | None = None):
    user_id = user_id or msg.from_user.id
    question, answer = random.choice(QUESTIONS)
    await _send_question(msg, user_id, question, answer, 0, vault=False)


@router.message(Command("daily"))
async def daily(msg: types.Message):
    await show_daily(msg, msg.from_user)


async def show_daily(message: types.Message, user: types.User, notice: str | None = None):
    await ensure_user(user)
    data = await get_user(user.id)
    streak = data[9] if data and data[9] else 0
    text = (
        "🔥 GUARDIAN DAILY ACTIVITY\n\n"
        f"🛡️ Current rank: {data[8] if data and len(data) > 8 else 'Initiate'}\n"
        "Defend the Vault each day to build your streak.\n"
        "⚡ Daily Guardian bonus: +5 Energy\n"
        "🎯 Daily challenge: +10 Energy\n"
        "🔥 Every seventh consecutive day: +25 streak bonus\n\n"
        f"Current streak: {streak} day{'s' if streak != 1 else ''}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👁️ Oria remembers every return."
    )
    if notice:
        text = f"{notice}\n\n{text}"
    await send_screen(message, text, _daily_menu_keyboard(), "Daily Guardian Activity")


@router.callback_query(F.data.startswith("daily:"))
async def handle_daily_action(callback: types.CallbackQuery):
    if not callback.message or not callback.data:
        await callback.answer("Daily activity is unavailable.", show_alert=True)
        return

    action = callback.data.partition(":")[2]
    today = _today()
    if action == "claim":
        await callback.answer()
        claimed, streak, energy = await claim_daily(callback.from_user.id, today)
        if claimed:
            bonus = 25 if streak % 7 == 0 else 0
            notice = (
                f"✅ Daily bonus claimed: +{5 + bonus} Energy.\n"
                f"🔥 {streak}-day streak"
            )
            if bonus:
                notice += "\n✨ Seven-day streak bonus: +25 Energy"
            notice += f"\n⚡ Total Energy: {energy:,}"
        else:
            notice = f"🛡️ Daily bonus already claimed today.\n🔥 Current streak: {streak} day(s)."
        await show_daily(callback.message, callback.from_user, notice)
        return

    if action == "challenge":
        question, answer = random.choice(QUESTIONS)
        status, question, answer = await start_daily_challenge(
            callback.from_user.id, today, question, answer
        )
        if status == "completed":
            await callback.answer()
            await show_daily(callback.message, callback.from_user, "✅ Today's Daily Challenge is complete.")
            return
        if question is None or answer is None:
            await callback.answer("The daily challenge could not be loaded.", show_alert=True)
            return
        await callback.answer()
        await send_screen(
            callback.message,
            "🧠 DAILY CHALLENGE\n\n"
            "One signal. One answer. +10 Energy on completion.\n"
            f"👁️ Oria presents: {question}",
            _daily_keyboard(callback.from_user.id, today, answer),
            "Daily Challenge",
        )
        return

    await callback.answer("Unknown daily activity.", show_alert=True)


@router.callback_query(F.data.startswith("dailyanswer:"))
async def handle_daily_answer(callback: types.CallbackQuery):
    if not callback.message or not callback.data:
        await callback.answer("This daily signal is unavailable.", show_alert=True)
        return
    try:
        _, user_id_text, challenge_date, answer = callback.data.split(":", 3)
        user_id = int(user_id_text)
    except (ValueError, TypeError):
        await callback.answer("Invalid daily answer.", show_alert=True)
        return
    if user_id != callback.from_user.id or challenge_date != _today():
        await callback.answer("This daily challenge is no longer active.", show_alert=True)
        return

    correct, energy = await complete_daily_challenge(user_id, challenge_date, answer.casefold())
    if correct:
        await callback.answer("Daily challenge complete!")
        await show_daily(
            callback.message,
            callback.from_user,
            f"✅ Challenge complete: +10 Energy.\n⚡ Total Energy: {energy:,}",
        )
        return

    data = await get_user(user_id)
    if data and data[14] == challenge_date:
        await callback.answer("Today's challenge is already complete.", show_alert=True)
    elif data and data[16] == challenge_date and data[17]:
        await callback.answer("Not quite. Oria's signal is unchanged.", show_alert=True)
    else:
        await callback.answer("Today's challenge is no longer active.", show_alert=True)


@router.message()
async def handle_answers(msg: types.Message):
    if not msg.from_user:
        return
    await ensure_user(msg.from_user)
    user_id = msg.from_user.id

    if not msg.text or msg.text.startswith("/"):
        return
    if user_id not in current_answers:
        return

    await handle_answer_for_user(user_id, msg.from_user, msg, msg.text.strip().casefold())
