from app.users.models import User, AdminChat
from app.users import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert
from typing import Sequence, Iterable


# ---------- User ----------
async def create_user(session, *, first_name, last_name, nickname, telegram_id) -> User:
  user = User(
    first_name=first_name,
    last_name=last_name,
    nickname=nickname,
    telegram_id=telegram_id,
    is_active=False,
  )
  session.add(user)
  await session.flush()
  return user

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
  res = await session.execute(select(User).where(User.telegram_id == telegram_id))
  return res.scalar_one_or_none()

async def activate_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> bool:
  res = await session.execute(
    update(User)
      .where(User.telegram_id == telegram_id)
      .values(is_active=True)
      .returning(User.telegram_id)
  )
  return res.scalar_one_or_none() is not None

async def delete_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> bool:
  res = await session.execute(
    delete(User)
      .where(User.telegram_id == telegram_id)
      .returning(User.telegram_id)
  )
  return res.scalar_one_or_none() is not None


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_by_telegram(session: AsyncSession, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return result.scalars().all()


async def update_user(session: AsyncSession, telegram_id: int, data: schemas.UserUpdate) -> User:
    user = await get_user(session, telegram_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user

async def delete_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await session.delete(user)
    await session.commit()
    return {"detail": "User deleted"}


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_user(session, telegram_id)
    return user.is_admin


async def add_many(session: AsyncSession, items: Iterable[tuple[int, str | None]]) -> int:
    # ON CONFLICT DO NOTHING — игнорируем дубликаты
    stmt = insert(AdminChat).values([
        {"telegram_id": tid} for tid in items
    ]).on_conflict_do_nothing(index_elements=[AdminChat.telegram_id])
    res = await session.execute(stmt)
    return res.rowcount or 0

async def add_one(session: AsyncSession, telegram_id: int) -> None:
    await add_many(session, [(telegram_id)])

async def list_all(session: AsyncSession) -> Sequence[AdminChat]:
    res = await session.execute(select(AdminChat).order_by(AdminChat.created_at.desc()))
    return res.scalars().all()

async def remove(session: AsyncSession, telegram_id: int) -> int:
    res = await session.execute(delete(AdminChat).where(AdminChat.telegram_id == telegram_id))
    return res.rowcount or 0