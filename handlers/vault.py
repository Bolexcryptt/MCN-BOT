from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import random
from datetime import datetime

from db import add_points, add_vault_completion, ensure_user
from handlers.navigation import back_keyboard
from data.store import (
    user_points,
    last_vault,
)

router = Router()

# ---------------- QUESTIONS ----------------
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

# ---------------- STATES ----------------
vault_users = {}
question_users = {}

current_answers = {}

TOTAL_VAULT_QUESTIONS = 5


# =====================================================
# VAULT SYSTEM
# =====================================================


def build_answer_keyboard(user_id: int, options: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [InlineKeyboardButton(text=option, callback_data=f"answer:{user_id}:{option}")]
                for option in options
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")],
        ]
    )


def clear_user_session(user_id: int):
    if user_id in vault_users:
        vault_users.pop(user_id, None)
        last_vault.pop(user_id, None)
    question_users.pop(user_id, None)
    current_answers.pop(user_id, None)


async def handle_answer_for_user(user_id: int, user: types.User, message: types.Message, answer: str):
    if user_id not in current_answers:
        return

    correct = current_answers[user_id]

    if user_id in vault_users:
        if answer == correct:
            vault_users[user_id] += 1
            await add_points(user, 5)

            user_points[user_id] = user_points.get(user_id, 0) + 5

            await message.answer(f"""
✔ Correct  

⚡ +5 energy  
Total Energy: {user_points[user_id]}
""")

            if vault_users[user_id] >= TOTAL_VAULT_QUESTIONS:
                await add_vault_completion(user_id)
                vault_users.pop(user_id, None)
                current_answers.pop(user_id, None)

                await message.answer("""
✨ You have proven yourself  

You entered the Vault 🟦

Oria watches 👁️
                """, reply_markup=back_keyboard())

                return

            await send_vault_question(message, user_id)
            return

        await message.answer("""
❌ Incorrect  

Another Vault trial begins...
""")
        await send_vault_question(message, user_id)
        return

    if user_id in question_users:
        if answer == correct:
            await add_points(user, 1)
            user_points[user_id] = user_points.get(user_id, 0) + 1

            await message.answer(f"""
✔ Correct  

⚡ +1 energy  
Total Energy: {user_points[user_id]}
""")
            await send_question(message, user_id)
            return

        await message.answer("""
❌ Incorrect  

Another trial begins...
""")
        await send_question(message, user_id)


@router.callback_query(F.data.startswith("answer:"))
async def handle_button_answer(callback: types.CallbackQuery):
    if not callback.message or not callback.data:
        return

    try:
        _, user_id_str, answer = callback.data.split(":", 2)
        user_id = int(user_id_str)
        selected_answer = answer.strip().lower()
    except (ValueError, TypeError):
        await callback.answer("Invalid answer.", show_alert=True)
        return

    if callback.from_user.id != user_id or user_id not in current_answers:
        await callback.answer("This question is no longer active.", show_alert=True)
        return

    await callback.answer()
    await handle_answer_for_user(user_id, callback.from_user, callback.message, selected_answer)

@router.message(Command("vault"))
async def start_vault(msg: types.Message):
    await ensure_user(msg.from_user)
    user_id = msg.from_user.id
    today = datetime.now().date()

    # daily vault limit
    if last_vault.get(user_id) == today:
        await msg.answer("""
⚠️ You already entered the Vault today 👁️

Return tomorrow, Guardian.
""", reply_markup=back_keyboard())
        return

    last_vault[user_id] = today

    vault_users[user_id] = 0

    await msg.answer("""
🛡️ Vault Access Initiated  

Oria is watching 👁️
""")

    await send_vault_question(msg)


async def send_vault_question(msg: types.Message, user_id: int | None = None):
    user_id = user_id or msg.from_user.id

    question, answer = random.choice(QUESTIONS)

    wrong = random.choice(
        [q[1] for q in QUESTIONS if q[1] != answer]
    )

    options = [answer, wrong]
    random.shuffle(options)

    current_answers[user_id] = answer

    kb = build_answer_keyboard(user_id, options)

    progress = vault_users[user_id]

    await msg.answer(f"""
⚠️ Vault Trial  

🐾 Question {progress + 1}/{TOTAL_VAULT_QUESTIONS}

{question}
""", reply_markup=kb)


# =====================================================
# QUESTIONS SYSTEM
# =====================================================

@router.message(Command("questions"))
async def start_questions(msg: types.Message):
    await ensure_user(msg.from_user)
    user_id = msg.from_user.id

    question_users[user_id] = True

    await msg.answer("""
🧪 Guardian Trials Activated  

Gain energy ⚡  
Oria is watching 👁️
""")

    await send_question(msg)


async def send_question(msg: types.Message, user_id: int | None = None):
    user_id = user_id or msg.from_user.id

    question, answer = random.choice(QUESTIONS)

    wrong = random.choice(
        [q[1] for q in QUESTIONS if q[1] != answer]
    )

    options = [answer, wrong]
    random.shuffle(options)

    current_answers[user_id] = answer

    kb = build_answer_keyboard(user_id, options)
    await msg.answer(f"""
⚡ Trial Question  

{question}
""", reply_markup=kb)


# =====================================================
# ANSWER HANDLER
# =====================================================

@router.message()
async def handle_answers(msg: types.Message):
    await ensure_user(msg.from_user)
    user_id = msg.from_user.id

    # ignore commands
    if not msg.text or msg.text.startswith("/"):
        return

    # no active mode
    if user_id not in current_answers:
        return

    answer = msg.text.lower().strip()
    await handle_answer_for_user(user_id, msg.from_user, msg, answer)