from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

HOME_TEXT = """
🐾 Welcome, Guardian  

You have entered the MCN system.  
Oria is watching 👁️  

━━━━━━━━━━━━━━━  

🛡️ enter the Vault  
🧪 defend vault  
⚡ Earn energy  
🏆 Rise through ranks  

━━━━━━━━━━━━━━━  

Commands:
/vault  
/leaderboard  
/invite  
/questions  
/me  

━━━━━━━━━━━━━━━  

The Vault is waiting… 🟦
"""


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="navigation:home")]
        ]
    )


async def send_home(message: types.Message):
    await message.answer(HOME_TEXT)


@router.callback_query(F.data == "navigation:home")
async def back_to_home(callback: types.CallbackQuery):
    await callback.answer()
    if callback.message:
        from handlers.vault import clear_user_session

        clear_user_session(callback.from_user.id)
        await callback.message.edit_text(HOME_TEXT)