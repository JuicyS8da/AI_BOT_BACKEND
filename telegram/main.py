import asyncio
from telegram.core import dp, bot
from telegram import moderation

async def main():
    # подключаем все роутеры
    dp.include_router(moderation.router)

    print("🤖 Telegram bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
