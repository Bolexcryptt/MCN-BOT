import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from db import init_db

from handlers import user, vault, profile, invite, leaderboard, navigation

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(user.router)
dp.include_router(profile.router)
dp.include_router(invite.router)
dp.include_router(leaderboard.router)
dp.include_router(vault.router)  # keep vault LAST
dp.include_router(navigation.router)

async def main():
    await init_db()
    print("Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())