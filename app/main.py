import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.common.db import init_models, AsyncSessionLocal
from app.common.common import init_admin
from app.users.routers import router as user_router
from app.events.routers import router as event_router
from app.quizes.routers import router as quiz_router

app = FastAPI(title="Music Schedule Bot 6")

Path("media").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(user_router)
app.include_router(event_router)
app.include_router(quiz_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_models()
    asyncio.create_task(seed_admins())

async def seed_admins():
    async with AsyncSessionLocal() as session:
        await init_admin(session=session, telegram_id=1046929828, nickname="Birzhanova Adel", first_name="Adel", last_name="Birzhanova")
        await init_admin(session=session, telegram_id=707309709, nickname="Zakharov Aleksei", first_name="Aleksei", last_name="Zakharov")
        await init_admin(session=session, telegram_id=1131290603, nickname="Abdumanap Zhanibek", first_name="Zhanibek", last_name="Abdumanap")
        await init_admin(session=session, telegram_id=1234, nickname="Test Admin", first_name="Test", last_name="Admin")

@app.get("/")
async def root():
    return {"message": "Welcome to My Modular FastAPI Project"}
