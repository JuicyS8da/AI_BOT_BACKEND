from fastapi import APIRouter, Depends
from app.users import schemas
from app.users.services import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
async def register_user(user_data: schemas.UserCreate, service: UserService = Depends()):
    return await service.register_user(user_data)


@router.post("/check_admin")
async def check_admin(telegram_id: int, service: UserService = Depends()):
    return await service.check_admin(telegram_id)


@router.get("/", response_model=list[schemas.UserRead])
async def list_users(service: UserService = Depends()):
    return await service.list_users()


@router.get("/{telegram_id}", response_model=schemas.UserRead)
async def get_user(telegram_id: int, service: UserService = Depends()):
    return await service.get_user(telegram_id)


@router.delete("/{telegram_id}")
async def delete_user(telegram_id: int, service: UserService = Depends()):
    await service.delete_user(telegram_id)
    return {"detail": "User deleted"}
