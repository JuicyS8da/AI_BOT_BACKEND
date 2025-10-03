import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def parse_admin_ids(raw: str) -> list[int]:
    parts = [p.strip() for p in (raw or "").replace(";", ",").replace("\n", ",").split(",")]
    ids = []
    for p in parts:
        if not p:
            continue
        try:
            ids.append(int(p))
        except ValueError:
            print(f"[WARN] ADMIN_IDS skip: {p!r}")
    return ids

ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))
