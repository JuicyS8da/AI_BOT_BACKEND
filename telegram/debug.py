import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery

router = Router()

@router.message()
async def _any_msg(m: Message):
    logging.info(f"[MSG] chat={m.chat.id} from={m.from_user.id} text={m.text!r}")

@router.callback_query()
async def _any_cb(c: CallbackQuery):
    chat_id = c.message.chat.id if c.message else None
    logging.info(f"[CB] from={c.from_user.id} chat={chat_id} data={c.data!r}")
