from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from app.users import schemas
from app.common.db import get_async_session
from app.users.services import UserService
from app.users.services import AdminChatService
from app.common.common import CurrentUser
from app.users.models import User


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: schemas.UserRegisterIn, session: AsyncSession = Depends(get_async_session)):
  user = await UserService.register(session, payload)
  return user


@router.post("/check_admin")
async def check_admin(telegram_id: int, service: UserService = Depends()):
    return await service.check_admin(telegram_id)


@router.get("/list", response_model=list[schemas.UserRead])
async def list_users(service: UserService = Depends()):
    return await service.list_users()


@router.get("/{telegram_id}", response_model=schemas.UserRead)
async def get_user(telegram_id: int, service: UserService = Depends()):
    return await service.get_user(telegram_id)


@router.delete("/delete/{target_telegram_id}", summary="Удалить пользователя (только для админов)")
async def delete_user(
    target_telegram_id: int,
    service: UserService = Depends(),
):
    return await service.delete_user_as_admin(target_telegram_id)

# ADMIN NOTIFICATIONS

admin_router = APIRouter(prefix="/admin-chat", tags=["admin-chat"])

@admin_router.get("/", summary="Список участников admin chat (сырой)")
async def get_admin_chat_ids(
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(CurrentUser(require_admin=True)),
):
    rows = await AdminChatService.list_all(session)
    return {"count": len(rows), "telegram_ids": [r.telegram_id for r in rows]}

@admin_router.get("/users", response_model=list[schemas.UserOut], summary="Список участников admin chat c данными пользователя")
async def get_admin_chat_users(
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(CurrentUser(require_admin=True)),
):
    pairs = await AdminChatService.list_all_with_users(session)
    # берём только тех, у кого есть профиль
    users = [p[1] for p in pairs if p[1] is not None]
    return [schemas.UserOut.model_validate(u) for u in users]

@admin_router.post("/add", summary="Добавить одного участника по telegram_id")
async def add_admin_chat_member(
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(CurrentUser(require_admin=True)),
):
    await AdminChatService.add_one(session, telegram_id=telegram_id)
    return {"status": "ok", "telegram_id": telegram_id}

@admin_router.post("/add-many", summary="Добавить несколько участников")
async def add_admin_chat_many(
    telegram_ids: List[int],
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(CurrentUser(require_admin=True)),
):
    inserted = await AdminChatService.add_many(session, telegram_ids)
    return {"status": "ok", "inserted": inserted, "requested": len(telegram_ids)}

@admin_router.delete("/remove", summary="Удалить участника по telegram_id")
async def remove_admin_chat_member(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(CurrentUser(require_admin=True)),
):
    ok = await AdminChatService.remove(session, telegram_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found in admin chat")
    return {"status": "ok", "removed": telegram_id}