# app/main.py
import asyncio
import logging
import os
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.db import init_models, AsyncSessionLocal
from app.common.common import init_admin

# ваши API-роутеры
from app.users.routers import router as user_router
from app.users.routers import admin_router as admin_chat_router
from app.events.routers import router as event_router
from app.quizes.routers import router as quiz_router

# Telegram ядро
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
logger = logging.getLogger("uvicorn.error")
app_state_started = False  # защита от двойного запуска


# === Проверка BOT_TOKEN перед запуском ===
async def verify_bot_identity():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN is not set in environment variables")

    # базовая проверка формата токена
    if not re.fullmatch(r"\d{7,12}:[A-Za-z0-9_-]{35,}", token):
        raise RuntimeError("❌ BOT_TOKEN format looks invalid")

    # проверка соответствия id в токене и id из getMe()
    me = await bot.get_me()  # упадёт Unauthorized, если токен неверен
    token_bot_id = token.split(":")[0]
    if str(me.id) != token_bot_id:
        raise RuntimeError(
            f"❌ BOT_TOKEN mismatch: token bot_id={token_bot_id} but getMe.id={me.id}"
        )

    logger.info(f"✅ Bot OK: @{me.username} (id={me.id}), token_tail=...{token[-6:]}")


@app.on_event("startup")
async def startup_event():
    global bot_task, app_state_started
    if app_state_started:
        # уже инициализировали приложение/бота — выходим
        return
    app_state_started = True

    # жёсткая проверка токена до любых сетапов бота
    await verify_bot_identity()

    # БД/сиды
    await init_models()
    asyncio.create_task(seed_admins())

    # Запуск бота фоном
    async def run_bot():
        try:
            me = await bot.get_me()
            logger.info(f"🤖 Bot: @{me.username} (id={me.id}) starting…")
            # сброс вебхука, чтобы исключить 409 и висящие апдейты
            info = await bot.get_webhook_info()
            logger.info(f"Webhook before delete: url={info.url!r}, pending={info.pending_update_count}")
            await bot.delete_webhook(drop_pending_updates=True)

            used = dp.resolve_used_update_types()
            logger.info(f"ALLOWED_UPDATES = {used}")
            await dp.start_polling(bot, allowed_updates=used)
        except asyncio.CancelledError:
            logger.info("Bot polling cancelled (shutdown).")
            raise
        except Exception as e:
            logger.exception(f"Bot crashed: {e}")

    if not bot_task or bot_task.done():
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
