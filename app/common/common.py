from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends
from sqlalchemy import select

from app.common.db import get_async_session
from app.users.models import User

class CurrentUser:
    def __init__(self, require_admin: bool = False):
        self.require_admin = require_admin

    async def __call__(self, session: AsyncSession = Depends(get_async_session), telegram_id: int = 0):
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(401, "User not found")
        if self.require_admin and not user.is_admin:
            raise HTTPException(403, "Admin rights required")
        return user

async def init_admin(session, telegram_id: int, nickname: str):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        print(f"ℹ️ Админ {nickname} уже существует")
        return user
    new_admin = User(telegram_id=telegram_id, nickname=nickname, is_admin=True, is_active=True)
    session.add(new_admin)
    await session.commit()
    await session.refresh(new_admin)
    print(f"✅ Админ {nickname} создан")
    return {"id": new_admin.id, "nickname": new_admin.nickname}

