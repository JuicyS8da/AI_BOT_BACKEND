from typing import Optional, List

from pydantic import BaseModel, Field

class UserBase(BaseModel):
    telegram_id: int
    nickname: str = Field(..., min_length=3, max_length=30)

class UserCreate(UserBase):
    pass


class UserRegisterIn(BaseModel):
  first_name: str = Field(min_length=1, max_length=100)
  last_name:  str = Field(min_length=1, max_length=100)
  nickname:   str = Field(min_length=2, max_length=100)
  telegram_id: int

class UserOut(BaseModel):
  id: int
  first_name: str
  last_name: str
  nickname: str
  is_active: bool
  telegram_id: int

  class Config:
    from_attributes = True

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

class AdminChatIn(BaseModel):
    telegram_id: int

class AdminChatBulkIn(BaseModel):
    items: list[int]

class AdminChatOut(BaseModel):
    telegram_id: int

    class Config:
        from_attributes = True