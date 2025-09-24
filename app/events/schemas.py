# schemas.py
from pydantic import BaseModel
from typing import Optional, List
from app.events.models import EventStatus  # или свой Enum импортни

class QuizBriefOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class EventOut(BaseModel):
    id: int
    name: str
    status: EventStatus
    current_question_index: int
    creator_id: int
    quizes: List[QuizBriefOut] = []

    class Config:
        from_attributes = True
