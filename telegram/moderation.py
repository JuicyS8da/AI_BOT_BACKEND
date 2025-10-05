from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from telegram.core import bot
from app.common.db import get_async_session
from sqlalchemy import text, select
from app.users.models import AdminChat

router = Router()

def moderation_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Активировать", callback_data=f"approve_tg:{telegram_id}"),
        InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"reject_tg:{telegram_id}"),
    ]])

async def fetch_admin_ids() -> list[int]:
    async for session in get_async_session():
        res = await session.execute(select(AdminChat.telegram_id))
        return [row[0] for row in res.all()]
    return []

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
        f"Никнейм: @{nickname}\n\n"
        "Одобрить пользователя?"
    )
    kb = moderation_kb(telegram_id)

    for chat_id in admin_ids:
        try:
            await bot.send_message(chat_id, text_msg, reply_markup=kb)
        except Exception as e:
            print(f"[TG] failed to send to {chat_id}: {e}")

@router.callback_query(F.data.startswith("approve_tg:"))
async def on_approve(call: CallbackQuery):
    telegram_id = int(call.data.split(":")[1])

    # 1) ACK СРАЗУ
    try:
        await call.answer("✅ Активируем…")
    except TelegramBadRequest:
        pass  # если просрочен — просто игнор

    # 2) Делаем работу
    async for session in get_async_session():
        await session.execute(
            text("UPDATE users SET is_active = TRUE WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        await session.commit()

    # 3) Обновляем сообщение / уведомляем
    try:
        await call.message.edit_text(f"✅ Пользователь {telegram_id} активирован.")
    except TelegramBadRequest:
        pass
    try:
        await bot.send_message(telegram_id, "🎉 Ваша учётная запись активирована.")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("reject_tg:"))
async def on_reject(call: CallbackQuery):
    telegram_id = int(call.data.split(":")[1])

    # 1) ACK СРАЗУ
    try:
        await call.answer("⏳ Удаляю…")
    except TelegramBadRequest:
        pass

    # 2) Делаем работу
    async for session in get_async_session():
        await session.execute(
            text("DELETE FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        await session.commit()

    # 3) Обновляем сообщение / уведомляем
    try:
        await call.message.edit_text(f"❌ Пользователь {telegram_id} удалён.")
    except TelegramBadRequest:
        pass
    try:
        await bot.send_message(telegram_id, "❌ Ваша заявка отклонена.")
    except TelegramBadRequest:
        pass
