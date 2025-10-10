# app/main.py
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.db import init_models, AsyncSessionLocal
from app.common.common import init_admin

# ваши API-роутеры
from app.users.routers import router as user_router
from app.users.routers import admin_router as admin_chat_router
from app.events.routers import router as event_router
from app.quizes.routers import router as quiz_router

# <-- NEW: импорт ядра бота и его роутеров
from telegram.core import bot, dp
from telegram import moderation  # + если есть другие: auth, debug и т.п.

app = FastAPI(title="Music Schedule Bot 6")

# API
app.include_router(user_router)
app.include_router(admin_chat_router)
app.include_router(event_router)
app.include_router(quiz_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# регистрируем tg-роутеры в диспетчере
dp.include_router(moderation.router)
# dp.include_router(auth.router)

bot_task: asyncio.Task | None = None
logger = logging.getLogger("uvicorn.error")  # общий логгер uvicorn

@app.on_event("startup")
async def startup_event():
    # БД/сиды
    await init_models()
    asyncio.create_task(seed_admins())

    # Запуск бота фоном
    async def run_bot():
        try:
            me = await bot.get_me()
            logger.info(f"🤖 Bot: @{me.username} (id={me.id}) starting…")
            # на всякий: удалим вебхук и очистим очередь
            info = await bot.get_webhook_info()
            logger.info(f"Webhook before delete: url={info.url!r}, pending={info.pending_update_count}")
            await bot.delete_webhook(drop_pending_updates=True)
            # разрешаем нужные апдейты и стартуем polling
            used = dp.resolve_used_update_types()
            logger.info(f"ALLOWED_UPDATES = {used}")
            await dp.start_polling(bot, allowed_updates=used)
        except asyncio.CancelledError:
            logger.info("Bot polling cancelled (shutdown).")
            raise
        except Exception as e:
            logger.exception(f"Bot crashed: {e}")

    global bot_task
    bot_task = asyncio.create_task(run_bot())

@app.on_event("shutdown")
async def shutdown_event():
    global bot_task
    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass

async def seed_admins():
    async with AsyncSessionLocal() as session:
        await init_admin(session=session, telegram_id=1046929828, nickname="Birzhanova Adel", first_name="Adel", last_name="Birzhanova")
        await init_admin(session=session, telegram_id=707309709, nickname="Zakharov Aleksei", first_name="Aleksei", last_name="Zakharov")
        await init_admin(session=session, telegram_id=1131290603, nickname="Abdumanap Zhanibek", first_name="Zhanibek", last_name="Abdumanap")
        await init_admin(session=session, telegram_id=1234, nickname="Test Admin", first_name="Test", last_name="Admin")

@app.get("/")
async def root():
    return {"message": "Welcome to My Modular FastAPI Project"}
