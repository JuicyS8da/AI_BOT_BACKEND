from typing import Optional

from pydantic import BaseModel, Field

class UserBase(BaseModel):
    telegram_id: int
    nickname: str = Field(..., min_length=3, max_length=30)

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True

class UserRead(BaseModel):
    id: int
    telegram_id: int
    nickname: str
    is_active: bool
    is_admin: bool
    points: int

    class Config:
        orm_mode = True