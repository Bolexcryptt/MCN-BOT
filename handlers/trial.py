from aiogram import types, Router
from aiogram.filters import Command
from db import add_points
from config import EARLY_BONUS_LIMIT

router = Router()

trial_active = False
trial_users = set()

@router.message(Command("trial"))
async def start_trial(msg: types.Message):
    global trial_active, trial_users
    trial_active = True
    trial_users.clear()

    await msg.reply("🧪 Trial active — type DONE")

@router.message(Command("endtrial"))
async def end_trial(msg: types.Message):
    global trial_active
    trial_active = False

    await msg.reply(f"Trial ended. Participants: {len(trial_users)}")

@router.message()
async def handle_trial(msg: types.Message):
    global trial_active

    if not trial_active:
        return

    if msg.text.lower() != "done":
        return

    user = msg.from_user

    if user.id in trial_users:
        await msg.reply("❌ Already completed")
        return

    trial_users.add(user.id)

    if len(trial_users) <= EARLY_BONUS_LIMIT:
        await add_points(user, 4)
        await msg.reply("🔥 Early bonus +4")
    else:
        await add_points(user, 1)
        await msg.reply("✅ +1 point")