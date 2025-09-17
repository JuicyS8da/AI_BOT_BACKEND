from datetime import datetime
from pydantic import BaseModel, validator, Field
from typing import List

from datetime import datetime

DATETIME_FORMAT = "%d.%m.%Y %H:%M"

class MinigameCreate(BaseModel):
    name: str
    description: str | None = None
    duration_seconds: int = 60
    start_time: datetime = Field(examples=["20.09.2025 16"])

    @validator("start_time", pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, DATETIME_FORMAT)
        return v


class MinigameOut(BaseModel):
    id: int
    name: str
    description: str | None
    duration_seconds: int
    start_time: str  # возвращаем в строковом формате

    class Config:
        orm_mode = True

    @validator("start_time", pre=True)
    def format_datetime(cls, v: datetime):
        if isinstance(v, datetime):
            return v.strftime(DATETIME_FORMAT)
        return v


class MinigameQuestionCreate(BaseModel):
    text: str
    correct_answers: List[str] = []
    options: List[str] = []
    points: int = 1
    minigame_id: int

class MinigameQuestionOut(BaseModel):
    id: int
    text: str
    correct_answers: List[str]
    points: int
    type: str
    minigame_id: int

    class Config:
        orm_mode = True

class UserAnswerCreate(BaseModel):
    question_id: int
    answer: str


class UserAnswerOut(BaseModel):
    id: int
    user_id: int
    question_id: int
    answer: str
    minigame_id: int

    class Config:
        orm_mode = True

class UserAnswerResponse(BaseModel):
    id: int
    question_id: int
    minigame_id: int
    answer: str
    points_awarded: int
    total_user_points: int

    class Config:
        orm_mode = True
