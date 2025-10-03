from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users import crud, schemas
from app.users.models import User
from app.users.models import AdminChat
from telegram.moderation import notify_admins_new_user


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
    @staticmethod
    async def register(session: AsyncSession, data: schemas.UserRegisterIn) -> User:
        nickname = data.nickname.strip()

        # 1) Если этот telegram_id уже зарегистрирован — обновим данные
        q = await session.execute(
        select(User).where(User.telegram_id == data.telegram_id)
        )
        existing = q.scalar_one_or_none()
        if existing:
      # ник меняем только если он либо тот же, либо свободен
            if existing.nickname != nickname:
                nick_used = await session.execute(
                select(User.id).where(User.nickname == nickname)
                )
                if nick_used.scalar_one_or_none():
                    raise HTTPException(status_code=409, detail="nickname_taken")
            existing.first_name = data.first_name.strip()
            existing.last_name  = data.last_name.strip()
            existing.nickname   = nickname
            await session.commit()
            return existing

        # 2) Новый telegram_id: проверим ник
        nick_used = await session.execute(
            select(User.id).where(User.nickname == nickname)
        )
        if nick_used.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="nickname_taken")

        # 3) Создаём
        user = await crud.create_user(
            session,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            nickname=nickname,
            telegram_id=data.telegram_id,
        )
        await session.commit()

        await notify_admins_new_user(
            telegram_id=user.telegram_id,
            first_name=user.first_name,
            last_name=user.last_name,
            nickname=user.nickname,
        )
        return user

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

class AdminChatService:
    @staticmethod
    async def list_all(session: AsyncSession) -> list[AdminChat]:
        res = await session.execute(select(AdminChat).order_by(AdminChat.created_at.desc()))
        return list(res.scalars().all())

    @staticmethod
    async def add_one(session: AsyncSession, *, telegram_id: int) -> None:
        stmt = (
            insert(AdminChat)
            .values(telegram_id=telegram_id)
            .on_conflict_do_nothing(index_elements=[AdminChat.telegram_id])
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def add_many(session: AsyncSession, items: list[tuple[int]]) -> int:
        if not items:
            return 0
        stmt = (
            insert(AdminChat)
            .values([{"telegram_id": tid} for tid in items])
            .on_conflict_do_nothing(index_elements=[AdminChat.telegram_id])
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount or 0

    @staticmethod
    async def remove(session: AsyncSession, telegram_id: int) -> bool:
        res = await session.execute(delete(AdminChat).where(AdminChat.telegram_id == telegram_id))
        await session.commit()
        return (res.rowcount or 0) > 0
