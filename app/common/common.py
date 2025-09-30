from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends
from sqlalchemy import select
from typing import Optional, Annotated
from fastapi import Query

from app.common.db import get_async_session
from app.users.models import User

class CurrentUser:
    def __init__(self, require_admin: bool = False, optional: bool = False):
        self.require_admin = require_admin
        self.optional = optional

    async def __call__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user_telegram_id: Optional[int] = Query(
            None, alias="current_user_telegram_id", description="Telegram ID текущего пользователя"
        ),
    ) -> Optional[User]:
        # если id не передан
        if current_user_telegram_id is None:
            if self.optional:
                return None
            raise HTTPException(status_code=401, detail="Not authenticated")

        # ищем пользователя
        res = await session.execute(select(User).where(User.telegram_id == current_user_telegram_id))
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # проверка прав
        if self.require_admin and not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")

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

