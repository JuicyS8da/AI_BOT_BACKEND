from typing import Dict, List, Union, Optional
from pydantic import BaseModel
from app.quizes.models import QuestionType

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
    type: QuestionType | str
    text_i18n: Dict[str, str]
    options_i18n: Dict[str, List[str]] = {}
    correct_answers_i18n: Dict[str, List[str]] = {}
    duration_seconds: Optional[int] = 60
    points: int = 1
    quiz_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "type": "single",
                "text_i18n": {
                    "ru": "Столица Казахстана?",
                    "kk": "Қазақстан астанасы?",
                    "en": "What is the capital of Kazakhstan?"
                },
                "options_i18n": {
                    "ru": ["Астана", "Алматы", "Шымкент"],
                    "kk": ["Астана", "Алматы", "Шымкент"],
                    "en": ["Astana", "Almaty", "Shymkent"]
                },
                "correct_answers_i18n": {
                    "ru": ["Астана"],
                    "kk": ["Астана"],
                    "en": ["Astana"]
                },
                "duration_seconds": 60,
                "points": 1,
                "quiz_id": 42
            }
        }

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
    quiz_id: int
    answers: Union[str, List[str]]
    locale: str = "ru"
