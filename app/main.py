import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.db import init_models, AsyncSessionLocal
from app.common.common import init_admin
from app.users.routers import router as user_router
from app.events.routers import router as event_router
from app.quizes.routers import router as quiz_router

app = FastAPI(title="Music Schedule Bot 6")

app.include_router(user_router)
app.include_router(event_router)
app.include_router(quiz_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify frontend URL like ["http://192.168.0.50:3000"]
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
        await init_admin(session=session, telegram_id=1046929828, nickname="Birzhanova Adel")
        await init_admin(session=session, telegram_id=707309709, nickname="Zakharov Aleksei")
        await init_admin(session=session, telegram_id=1131290603, nickname="Abdumanap Zhanibek")
        await init_admin(session=session, telegram_id=1234, nickname="Test Admin")

@app.get("/")
async def root():
    return {"message": "Welcome to My Modular FastAPI Project"}
