from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from app.users import schemas
from app.common.db import get_async_session
from app.users.services import UserService
from app.users.services import AdminChatService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: schemas.UserRegisterIn, session: AsyncSession = Depends(get_async_session)):
  user = await UserService.register(session, payload)
  return user


@router.post("/check_admin")
async def check_admin(telegram_id: int, service: UserService = Depends()):
    return await service.check_admin(telegram_id)


@router.get("/", response_model=list[schemas.UserRead])
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

@router.get("/", response_model=list[schemas.AdminChatOut])
async def get_admin_chats(session: AsyncSession = Depends(get_async_session)):
    return await AdminChatService.list_all(session)

@router.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def add_admin_chat(payload: schemas.AdminChatIn, session: AsyncSession = Depends(get_async_session)):
    await AdminChatService.add_one(session, telegram_id=payload.telegram_id, note=payload.note)

@router.post("/bulk", status_code=status.HTTP_200_OK)
async def add_admin_chats_bulk(payload: schemas.AdminChatBulkIn, session: AsyncSession = Depends(get_async_session)):
    inserted = await AdminChatService.add_many(session, [(tid) for tid in payload.items])
    return {"inserted": inserted}


@router.delete("/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_chat(telegram_id: int, session: AsyncSession = Depends(get_async_session)):
    ok = await AdminChatService.remove(session, telegram_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not_found")