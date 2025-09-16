from datetime import datetime
from pydantic import BaseModel, validator, Field
from typing import List, Optional

DATETIME_FORMAT = "%d.%m.%Y %H:%M"

class QuizBase(BaseModel):
    title: str
    description: Optional[str] = None


class QuizCreate(QuizBase):
    duration_seconds: int = 60
    start_time: datetime = Field(examples=["20.09.2025 16:00"])

    @validator("start_time", pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, DATETIME_FORMAT)
        return v


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class QuizRead(QuizBase):
    id: int

    class Config:
        from_attributes = True

class QuizQuestionBase(BaseModel):
    text: str


class QuizQuestionCreate(QuizQuestionBase):
    quiz_id: int


class QuizQuestionUpdate(BaseModel):
    text: Optional[str] = None


class QuizQuestionRead(QuizQuestionBase):
    id: int
    quiz_id: int

    class Config:
        from_attributes = True

class UserAnswerBase(BaseModel):
    user_id: int
    answer: str


class UserAnswerCreate(UserAnswerBase):
    question_id: int


class UserAnswerUpdate(BaseModel):
    answer: Optional[str] = None


class UserAnswerRead(UserAnswerBase):
    id: int
    question_id: int

    class Config:
        from_attributes = True