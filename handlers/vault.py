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
    (
        "👁️ Oria has watched over the Kingdom since its beginning. What is her role in the Guardian system?",
        "The Kingdom's watchful guide",
        "The Kingdom's appointed ruler",
    ),
    (
        "🏛️ The Vault is under threat. What is every Guardian expected to do?",
        "Stand together and defend it",
        "Withdraw and leave it unguarded",
    ),
    (
        "🛡️ A newcomer enters the Kingdom as a Guardian. What is their first responsibility?",
        "Protect and build the Kingdom",
        "Claim rank before serving",
    ),
    (
        "👑 A Guardian seeks the Royal Guardian path. What earns that progression?",
        "Proven service through the trials",
        "A title chosen at the entrance",
    ),
    (
        "🏰 What does the Vault represent at the heart of the MCN Kingdom?",
        "The Kingdom's shared stronghold",
        "A private throne for one Guardian",
    ),
    (
        "👁️ Why does Oria continually observe the Guardians?",
        "To witness and guide their actions",
        "To replace their choices with orders",
    ),
    (
        "🛡️ What separates a Guardian from an ordinary visitor?",
        "A duty to defend and build",
        "A right to rule without service",
    ),
    (
        "⚡ What does Energy signify in Guardian progression?",
        "Progress earned through participation",
        "A title granted at arrival",
    ),
    (
        "🏛️ When the Vault's defenses weaken, which response honors a Guardian's oath?",
        "Rally to restore its defenses",
        "Wait for another Guardian to act",
    ),
    (
        "👁️ Oria sees a Guardian complete a trial. What does that moment show?",
        "The Guardian has faced the test",
        "The Guardian now commands Oria",
    ),
    (
        "🛡️ A Guardian wants the Kingdom to grow stronger. Which path serves that purpose?",
        "Build alongside fellow Guardians",
        "Keep strength for themselves alone",
    ),
    (
        "🏰 The Kingdom faces a difficult season. What keeps its Guardians united?",
        "Their shared duty to the Vault",
        "A contest to abandon the weakest",
    ),
    (
        "👑 What does the Royal Guardian title mark in the Kingdom?",
        "A higher step earned through service",
        "A separate rank outside the trials",
    ),
    (
        "🧭 A Guardian has advanced beyond the Royal path. What does Ambassador represent?",
        "A Guardian trusted to represent MCN",
        "A Guardian released from the Kingdom",
    ),
    (
        "📜 A new trial is announced beneath Oria's gaze. Why do Guardians enter it?",
        "To prove their resolve through action",
        "To bypass the Kingdom's progression",
    ),
    (
        "🏛️ Why is the Vault central to the Guardian system?",
        "It is the stronghold they protect",
        "It is a prize kept by Oria alone",
    ),
    (
        "👁️ Oria watches Guardians make their own choices. What does her watchfulness reinforce?",
        "Accountability within the Kingdom",
        "Obedience without personal judgment",
    ),
    (
        "🛡️ A Guardian finds a breach in the Vault's defenses. What should happen next?",
        "Help defend and strengthen the breach",
        "Hide the breach to protect their rank",
    ),
    (
        "⚡ A Guardian gains Energy after a trial. What has that reward recorded?",
        "Their earned progression",
        "Their authority over other Guardians",
    ),
    (
        "🏰 What is the purpose of the MCN Kingdom?",
        "A community built and defended together",
        "A realm ruled by a lone champion",
    ),
    (
        "🛡️ Two Guardians disagree while defending the Vault. What should guide them?",
        "The Kingdom's shared purpose",
        "The highest ranker's personal gain",
    ),
    (
        "👑 Which path leads a Guardian toward becoming Royal?",
        "Continue serving through progression",
        "Skip the trials and claim the crown",
    ),
    (
        "🤝 A Guardian welcomes a new ally. How should they introduce the Kingdom?",
        "Invite them to protect and build",
        "Promise them rule over the Vault",
    ),
    (
        "👁️ Oria witnesses a Guardian help another. What does that act strengthen?",
        "Trust among the Guardians",
        "One Guardian's claim to the throne",
    ),
    (
        "🏛️ What is a Guardian protecting when they defend the Vault?",
        "The Kingdom and its shared future",
        "A personal store of rank titles",
    ),
    (
        "🛡️ What is expected of a Guardian after completing a trial?",
        "Return to the work of the Kingdom",
        "Leave the Vault to the next recruit",
    ),
    (
        "⚡ Why does Energy matter to a rising Guardian?",
        "It reflects earned advancement",
        "It replaces service to the Kingdom",
    ),
    (
        "🏰 A visitor asks who builds the MCN Kingdom. What is the Guardian's answer?",
        "Guardians build it together",
        "Oria builds it without the Guardians",
    ),
    (
        "👑 How should an Ambassador carry the MCN identity beyond the Vault?",
        "Represent the Kingdom with responsibility",
        "Speak only for their own rank",
    ),
    (
        "👁️ What is Oria's relationship to the Vault?",
        "She watches over its Guardians",
        "She owns it apart from the Kingdom",
    ),
    (
        "🛡️ A Guardian sees the Kingdom under pressure. What does their duty call for?",
        "Stand firm and help defend it",
        "Protect only their personal progress",
    ),
    (
        "📈 What does Kingdom progression ask of a Guardian?",
        "Grow through trials and service",
        "Collect titles without taking part",
    ),
    (
        "🏛️ Why do Guardians return to the Vault after a victory?",
        "Its defense remains a shared duty",
        "The Vault belongs to the latest victor",
    ),
    (
        "🤝 What makes the Guardian system stronger?",
        "Guardians supporting the Kingdom together",
        "Guardians competing to stand alone",
    ),
    (
        "👑 Which statement best describes the Royal Guardian path?",
        "A mark of deeper commitment",
        "An exit from Guardian responsibility",
    ),
    (
        "🧭 Why does the Kingdom need Ambassadors?",
        "To carry MCN's identity outward",
        "To replace Oria inside the Vault",
    ),
    (
        "👁️ A Guardian acts while Oria watches. What gives that action meaning?",
        "Choosing to serve the Kingdom",
        "Waiting for Oria to act instead",
    ),
    (
        "🏰 What should a Guardian's effort leave behind in the Kingdom?",
        "A stronger Vault and community",
        "A higher wall between Guardians",
    ),
    (
        "🛡️ The Vault is safe for now. Does a Guardian's duty end there?",
        "No, they keep building and defending",
        "Yes, service ends with each victory",
    ),
    (
        "⚡ How is a Guardian's progress best understood?",
        "As earned steps within the system",
        "As permission to ignore the system",
    ),
    (
        "📜 What does entering a Guardian trial mean?",
        "Accepting a test within the Kingdom",
        "Receiving an instant rank promotion",
    ),
    (
        "🏛️ A Guardian calls the Vault a shared stronghold. What follows from that?",
        "Its defense belongs to every Guardian",
        "Its keys belong to the oldest Guardian",
    ),
    (
        "👁️ Why does Oria witness both victories and failures?",
        "The trials reveal a Guardian's journey",
        "Only victories count as Kingdom history",
    ),
    (
        "🛡️ A Guardian has earned a higher rank. What should change?",
        "Their service and responsibility deepen",
        "Their duty to the Vault disappears",
    ),
    (
        "🏰 What does it mean to build the MCN Kingdom?",
        "Strengthen its community and purpose",
        "Keep its purpose hidden from Guardians",
    ),
    (
        "🤝 A Guardian recruits a new member. What are they bringing into the Kingdom?",
        "Another ally to build and defend",
        "A replacement for Oria's watch",
    ),
    (
        "👑 What is an Ambassador trusted to carry?",
        "The MCN identity and its purpose",
        "A private claim to the Vault",
    ),
    (
        "⚔️ A threat tests the Kingdom. What is the Guardian response?",
        "Unite to defend the Vault",
        "Wait for rank to defend itself",
    ),
    (
        "🌱 How does the Guardian community make the Kingdom endure?",
        "By building together over time",
        "By relying on one Guardian alone",
    ),
    (
        "👁️ Oria watches the Guardians progress. What does she witness?",
        "Their choices, trials and service",
        "A rank ladder with no participants",
    ),
    (
        "🏛️ What does a Guardian's place in the Vault community mean?",
        "They share in its defense and growth",
        "They stand above its shared purpose",
    ),
    (
        "🛡️ What is the first principle of Guardian duty?",
        "Protect the Kingdom and build it",
        "Seek a title before helping anyone",
    ),
    (
        "📈 How does a Guardian approach the next rank?",
        "Keep earning progress through action",
        "Ask Oria to skip their service",
    ),
    (
        "🏰 Why do the Guardians defend the Kingdom together?",
        "Its future is a shared responsibility",
        "Only the highest rank has a future",
    ),
    (
        "👑 What distinguishes an Ambassador's progression from a new Guardian's?",
        "Greater trust to represent MCN",
        "Freedom from every Guardian duty",
    ),
    (
        "🧭 A Guardian asks what to do after joining. What should guide their first steps?",
        "Learn the lore and serve the Kingdom",
        "Demand the highest rank immediately",
    ),
    (
        "⚡ What does each earned step of Energy represent?",
        "Participation in Guardian progression",
        "Ownership of another Guardian's effort",
    ),
    (
        "🏛️ Why must the Vault never be treated as one Guardian's prize?",
        "It stands at the heart of the Kingdom",
        "It is only a ladder to personal rule",
    ),
    (
        "👁️ What does Oria's presence remind each Guardian?",
        "Their actions are seen in the Kingdom",
        "Their choices belong to Oria alone",
    ),
    (
        "🛡️ What does it mean to defend and build the Kingdom?",
        "Protect its stronghold and help it grow",
        "Guard your title and leave it unchanged",
    ),
]

vault_users: dict[int, int] = {}
question_users: dict[int, bool] = {}
current_answers: dict[int, str] = {}
current_wrong_answers: dict[int, str] = {}
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


def _wrong_answer(question: str) -> str:
    for prompt, _answer, wrong in QUESTIONS:
        if prompt == question:
            return wrong
    raise ValueError(f"Question is not in the Guardian trial collection: {question!r}")


def _answer_options(answer: str, wrong_answer: str) -> list[str]:
    options = [answer, wrong_answer]
    random.shuffle(options)
    return options


def build_answer_keyboard(
    user_id: int,
    options: list[str],
    token: str = "manual",
    correct_answer: str | None = None,
) -> InlineKeyboardMarkup:
    correct_answer = correct_answer or options[0]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=(
                    f"answer:{user_id}:{token}:"
                    f"{'correct' if option == correct_answer else 'wrong'}"
                ),
            )]
            for option in options
        ] + [[InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")]]
    )


def _daily_keyboard(
    user_id: int,
    today: str,
    answer: str,
    wrong_answer: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=(
                    f"dailyanswer:{user_id}:{today}:"
                    f"{'correct' if option == answer else 'wrong'}"
                ),
            )]
            for option in _answer_options(answer, wrong_answer)
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
    current_wrong_answers.pop(user_id, None)
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
                current_wrong_answers.pop(user_id, None)
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
            current_wrong_answers.pop(user_id, None)
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
        current_wrong_answers.pop(user_id, None)
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
            current_wrong_answers.pop(user_id, None)
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
        current_wrong_answers.pop(user_id, None)
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
        _, user_id_str, token, choice = callback.data.split(":", 3)
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        await callback.answer("Invalid answer.", show_alert=True)
        return

    if (
        callback.from_user.id != user_id
        or user_id not in current_answers
        or current_tokens.get(user_id) != token
        or choice not in {"correct", "wrong"}
    ):
        await callback.answer("This question is no longer active.", show_alert=True)
        return

    await callback.answer()
    selected_answer = (
        current_answers[user_id]
        if choice == "correct"
        else current_wrong_answers[user_id]
    )
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
            await _send_question(
                message,
                user_id,
                question,
                answer,
                _wrong_answer(question),
                progress,
                vault=True,
            )
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
    question, answer, wrong_answer = random.choice(QUESTIONS)
    progress = vault_users.get(user_id, 0)
    await _send_question(
        msg,
        user_id,
        question,
        answer,
        wrong_answer,
        progress,
        vault=True,
        persist=persist,
    )


async def _send_question(
    message: types.Message,
    user_id: int,
    question: str,
    answer: str,
    wrong_answer: str,
    progress: int,
    vault: bool,
    persist: bool = False,
):
    correct_choice = answer
    wrong_choice = wrong_answer
    current_answers[user_id] = correct_choice.casefold()
    current_wrong_answers[user_id] = wrong_choice.casefold()
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
        build_answer_keyboard(
            user_id,
            _answer_options(correct_choice, wrong_choice),
            token,
            correct_answer=correct_choice,
        ),
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
    question, answer, wrong_answer = random.choice(QUESTIONS)
    await _send_question(msg, user_id, question, answer, wrong_answer, 0, vault=False)


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
        question, answer, wrong_answer = random.choice(QUESTIONS)
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
            _daily_keyboard(callback.from_user.id, today, answer, wrong_answer),
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
        _, user_id_text, challenge_date, choice = callback.data.split(":", 3)
        user_id = int(user_id_text)
    except (ValueError, TypeError):
        await callback.answer("Invalid daily answer.", show_alert=True)
        return
    if choice not in {"correct", "wrong"}:
        await callback.answer("Invalid daily answer.", show_alert=True)
        return
    if user_id != callback.from_user.id or challenge_date != _today():
        await callback.answer("This daily challenge is no longer active.", show_alert=True)
        return

    data = await get_user(user_id)
    if not data or data[15] != challenge_date or not data[17]:
        await callback.answer("Today's challenge is no longer active.", show_alert=True)
        return
    selected_answer = data[17] if choice == "correct" else _wrong_answer(data[16])
    correct, energy = await complete_daily_challenge(user_id, challenge_date, selected_answer)
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
