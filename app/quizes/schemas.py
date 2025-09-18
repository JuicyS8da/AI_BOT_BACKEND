from datetime import datetime
from pydantic import BaseModel, validator, Field
from typing import List, Optional

from datetime import datetime

class QuizCreate(BaseModel):
    name: str
    description: str | None = None


class QuizOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool

    class Config:
        orm_mode = True


class QuizQuestionCreate(BaseModel):
    text: str
    correct_answers: List[str] = []
    options: List[str] = []
    duration_seconds: Optional[int] = None
    points: int = 1
    quiz_id: int

class QuizQuestionOut(BaseModel):
    id: int
    text: str
    correct_answers: List[str]
    duration_seconds: Optional[int] = None
    points: int
    type: str
    quiz_id: int

    class Config:
        orm_mode = True

class UserAnswerCreate(BaseModel):
    question_id: int
    answers: List[str]
