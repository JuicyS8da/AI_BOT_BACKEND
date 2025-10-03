from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
from starlette import status

from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users import crud, schemas
from app.users.models import User
from app.events.models import Event, EventStatus


class UserService:
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: Annotated[Optional[User], Depends(CurrentUser(optional=True))] = None,
    ):
        self.session = session
        self.current_user = current_user

    # ===== Helpers =====
    def _require_auth(self) -> User:
        if not self.current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return self.current_user

    def _require_admin(self) -> User:
        user = self._require_auth()
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return user

    async def _get_user_by_telegram(self, telegram_id: int) -> Optional[User]:
        res = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return res.scalar_one_or_none()

    # ===== Public API =====
    async def register_user(self, user_data: schemas.UserCreate) -> dict:
        """
        Регистрация пользователя и автодобавление в активный Event со статусом STARTED.
        Авторизация не требуется.
        """
        # 1) проверки уникальности
        by_tg = await self._get_user_by_telegram(user_data.telegram_id)
        if by_tg:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "code": "TELEGRAM_ALREADY_REGISTERED", "message": "Этот Telegram уже зарегистрирован"},
            )

        res = await self.session.execute(select(User).where(User.nickname == user_data.nickname))
        by_nick = res.scalar_one_or_none()
        if by_nick:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "code": "NICKNAME_TAKEN", "message": "Этот никнейм уже занят"},
            )

        # 2) активный ивент для регистрации
        res = await self.session.execute(select(Event).where(Event.status == EventStatus.STARTED))
        active_event = res.scalar_one_or_none()
        if not active_event:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "code": "EVENT_IS_NOT_ACTIVE", "message": "Ивент либо ещё не начался, либо уже завершён"},
            )

        # 3) создаём пользователя + добавляем в игроков события
        new_user = User(telegram_id=user_data.telegram_id, nickname=user_data.nickname)
        active_event.players.append(new_user)

        self.session.add_all([new_user, active_event])
        await self.session.commit()
        return {"status": "success"}

    async def check_admin(self, telegram_id: int) -> dict:
        """Проверка прав админа по telegram_id (без текущей авторизации)."""
        user = await self._get_user_by_telegram(telegram_id)
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return {"status": "success"}

    async def list_users(self) -> list[User]:
        """Список пользователей (требует авторизацию администратора)."""
        self._require_admin()
        return await crud.list_users(self.session)

    async def get_user(self, telegram_id: int) -> User:
        """Получить пользователя по telegram_id (требует авторизацию)."""
        self._require_auth()
        user = await crud.get_user(self.session, telegram_id=telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def delete_user_as_admin(self, target_telegram_id: int) -> dict:
        # 1) Проверяем админа
        res = await self.session.execute(select(User).where(User.telegram_id == self.current_user.telegram_id))
        admin = res.scalar_one_or_none()
        if not admin or not admin.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")

        # 2) Ищем пользователя
        res = await self.session.execute(select(User).where(User.telegram_id == target_telegram_id))
        target = res.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        # 3) (опционально) запрещаем удаление других админов
        if target.is_admin and target.telegram_id != admin.telegram_id:
            raise HTTPException(status_code=403, detail="You cannot delete another admin")

        await self.session.delete(target)
        await self.session.commit()

        return {
            "status": "success",
            "message": f"User {target.nickname or target.telegram_id} deleted by admin {admin.nickname or admin.telegram_id}",
            "deleted_user_id": target.telegram_id,
            "admin_id": admin.telegram_id,
        }



    async def promote_to_admin(self, telegram_id: int) -> User:
        """Повысить пользователя до админа (только админ)."""
        self._require_admin()

        res = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        target = res.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if target.is_admin:
            raise HTTPException(status_code=400, detail="User is already an admin")

        target.is_admin = True
        self.session.add(target)
        await self.session.commit()
        await self.session.refresh(target)
        return target
