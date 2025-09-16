from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users import crud, schemas
from app.users.models import User
from app.events.models import Event, EventStatus


class UserService:
    def __init__(self, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
        self.session = session
        self.current_user = current_user

    async def register_user(self, user_data: schemas.UserCreate) -> dict:
        result = await self.session.execute(
            select(User).where(User.telegram_id == user_data.telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "code": "NICKNAME_TAKEN",
                    "message": "Этот никнейм уже занят",
                },
            )

        new_user = User(telegram_id=user_data.telegram_id, nickname=user_data.nickname)

        result = await self.session.execute(
            select(Event).where(Event.status == EventStatus.REGISTRATION)
        )
        active_event = result.scalar_one_or_none()
        if not active_event:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "code": "GAME_ALREADY_STARTED",
                    "message": "Регистрация уже завершена либо игра ещё не начата",
                },
            )

        active_event.players.append(new_user)
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)

        return {"status": "success"}

    async def check_admin(self, telegram_id: int) -> dict:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return {"status": "success"}

    async def list_users(self) -> list[User]:
        return await crud.list_users(self.session)

    async def get_user(self, telegram_id: int) -> User:
        return await crud.get_user(self.session, telegram_id=telegram_id)

    async def delete_user(self, telegram_id: int) -> None:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        await crud.delete_user(self.session, telegram_id=telegram_id)
    
    async def promote_to_admin(self, telegram_id: int) -> User:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")

        user = await self.session.get(User, telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_admin:
            raise HTTPException(status_code=400, detail="User is already an admin")

        user.is_admin = True
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
