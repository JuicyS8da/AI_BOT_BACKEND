import asyncio
from telegram.core import dp, bot
from telegram import moderation

async def main():
    # подключаем все роутеры
    dp.include_router(moderation.router)

    print("🤖 Telegram bot started...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(
    bot,
    allowed_updates=dp.resolve_used_update_types(),
)

if __name__ == "__main__":
    asyncio.run(main())
