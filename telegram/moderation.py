from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from telegram.core import bot
from app.common.db import get_async_session, AsyncSessionLocal
from sqlalchemy import text, select
from sqlalchemy.sql import text as sql_text
from app.users.models import AdminNotification

router = Router()

def moderation_kb(tid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Активировать", callback_data=f"approve_tg:{tid}")],
        [InlineKeyboardButton(text="🗑 Отклонить",    callback_data=f"reject_tg:{tid}")],
    ])

async def fetch_admin_ids() -> list[int]:
    # Если у тебя есть модель AdminChat — используй select(AdminChat.telegram_id)
    async with AsyncSessionLocal() as session:
        res = await session.execute(sql_text("SELECT telegram_id FROM admin_chats"))
        # scalars() вернёт список telegram_id
        return [int(x) for x in res.scalars().all()]

async def notify_admins_new_user(telegram_id: int, first_name: str, last_name: str, nickname: str):
    admin_ids = await fetch_admin_ids()
    if not admin_ids:
        print("[WARN] No admin chats configured (use /admin-chats).")
        return

    text_msg = (
        "<b>Новая регистрация</b>\n"
        f"Telegram ID: <code>{telegram_id}</code>\n"
        f"Имя: {first_name}\n"
        f"Фамилия: {last_name}\n"
        f"Никнейм: {nickname}\n\n"
        "Одобрить пользователя?"
    )
    kb = moderation_kb(telegram_id)

    # откроем сессию БД для записи уведомлений
    async with AsyncSessionLocal() as session:
        for chat_id in admin_ids:
            try:
                msg = await bot.send_message(chat_id, text_msg, reply_markup=kb)
                # если используешь таблицу admin_notifications:
                session.add(AdminNotification(
                    user_tid=telegram_id,
                    admin_chat_id=chat_id,
                    message_id=msg.message_id,
                    status="pending",
                ))
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                # чат не найден / бот заблокирован — просто лог и к следующему
                print(f"[TG] skip {chat_id}: {e}")
                continue

        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise

@router.callback_query(F.data.startswith("approve_tg:"))
async def on_approve(call: CallbackQuery):
    tid = int(call.data.split(":")[1])
    try:
        await call.answer("✅ Активируем…")
    except TelegramBadRequest:
        pass

    # 1) idempotent-апдейт пользователя: сработает только у первого нажатия
    async for s in get_async_session():
        res = await s.execute(
            text("""
                UPDATE users
                SET is_active = TRUE
                WHERE telegram_id = :tid AND is_active = FALSE
                RETURNING id
            """),
            {"tid": tid},
        )
        first_time = res.first() is not None

        # 2) помечаем уведомления и забираем все message_id
        notifs = (await s.execute(
            select(AdminNotification).where(AdminNotification.user_tid == tid)
        )).scalars().all()

        for n in notifs:
            n.status = "approved"
        await s.commit()

    # 3) редактируем/удаляем сообщения у всех админов
    text_all = f"✅ Пользователь {tid} активирован."
    for n in notifs:
        try:
            # можно удалить:
            # await bot.delete_message(n.admin_chat_id, n.message_id)
            # или отредактировать:
            await bot.edit_message_text(
                text_all,
                chat_id=n.admin_chat_id,
                message_id=n.message_id,
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            pass

    # 4) нажатому администратору отредактируем текущее сообщение (на случай, если оно не попало в цикл)
    try:
        await call.message.edit_text(text_all)
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("reject_tg:"))
async def on_reject(call: CallbackQuery):
    tid = int(call.data.split(":")[1])
    try:
        await call.answer("🗑 Отклоняем…")
    except TelegramBadRequest:
        pass

    async for s in get_async_session():
        # удаляем пользователя ИЛИ ставим is_active = FALSE/какой-то статус
        await s.execute(text("DELETE FROM users WHERE telegram_id = :tid"), {"tid": tid})

        notifs = (await s.execute(
            select(AdminNotification).where(AdminNotification.user_tid == tid)
        )).scalars().all()
        for n in notifs:
            n.status = "rejected"
        await s.commit()

    text_all = f"❌ Пользователь {tid} отклонён."
    for n in notifs:
        try:
            await bot.edit_message_text(
                text_all,
                chat_id=n.admin_chat_id,
                message_id=n.message_id,
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    try:
        await call.message.edit_text(text_all)
    except TelegramBadRequest:
        pass
