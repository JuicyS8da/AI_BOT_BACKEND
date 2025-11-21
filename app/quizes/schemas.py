from typing import Dict, List, Union, Optional, Literal
from pydantic import BaseModel, model_validator, Field, AnyUrl, ConfigDict
from app.quizes.models import QuestionType


class QuizCreate(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = False
    event_id: int


class QuizOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    event_id: int
    model_config = {"from_attributes": True}



class QuizQuestionCreate(BaseModel):
    type: QuestionType | str
    text_i18n: Dict[str, str]
    options_i18n: Dict[str, List[str]] = {}
    correct_answers_i18n: Dict[str, List[str]] = {}
    duration_seconds: Optional[int] = 60
    points: int = 1
    quiz_id: int
    images_urls: Optional[List[AnyUrl]] = None

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
    quiz_id: int
    # enum в ответе как строка
    type: Literal["single", "multiple", "open"]  # или QuestionType и добавить use_enum_values=True

    # валидируем с ORM-атрибутов *_i18n, отдаем как короткие имена
    text: Dict[str, str] = Field(validation_alias="text_i18n", serialization_alias="text")
    options: Dict[str, List[str]] = Field(default_factory=dict, validation_alias="options_i18n", serialization_alias="options")
    correct_answers: Dict[str, List[str]] = Field(default_factory=dict, validation_alias="correct_answers_i18n", serialization_alias="correct_answers")

    duration_seconds: Optional[int] = 60
    points: int = 1

    images_urls: List[str] = []

    model_config = {
        "from_attributes": True,     # можно пихать ORM объект
        "populate_by_name": True,    # уважать alias при инициализации
        "use_enum_values": True,     # если type: QuestionType — отдаст строки
    }


class UserAnswerCreate(BaseModel):
    question_id: int
    quiz_id: int
    answers: Union[str, List[str]]
    locale: str = "ru"

class QuizQuestionUpsert(BaseModel):
    type: QuestionType | str
    text_i18n: Dict[str, str]
    options_i18n: Dict[str, List[str]] = {}
    correct_answers_i18n: Dict[str, List[str]] = {}
    duration_seconds: Optional[int] = 60
    points: int = 1
    images_urls: Optional[List[AnyUrl]] = None

    model_config = ConfigDict(
        json_schema_extra={
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
                "images_urls": [
                    "https://example.com/images/q1-A.jpg",
                    "https://example.com/images/q1-B.jpg"
                ]
            }
        }
    )
    @model_validator(mode="after")
    def validate_choice_consistency(self):
        t = self.type.value if isinstance(self.type, QuestionType) else str(self.type)
        if t in ("single", "multiple"):
            for loc, correct in (self.correct_answers_i18n or {}).items():
                opts = set((self.options_i18n or {}).get(loc, []))
                if not opts:
                    raise ValueError(f"options_i18n[{loc}] is required for type={t}.")
                if not set(correct).issubset(opts):
                    raise ValueError(f"correct_answers_i18n[{loc}] must be subset of options_i18n[{loc}].")
            if t == "single":
                # необязательно строго, но полезно
                for loc, correct in (self.correct_answers_i18n or {}).items():
                    if len(correct) != 1:
                        raise ValueError(f"single requires exactly one correct answer for locale '{loc}'.")
        return self


class QuizQuestionsBulkIn(BaseModel):
    items: List[QuizQuestionUpsert]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "type": "multiple",
                        "text_i18n": {"ru": "Выберите гласные"},
                        "options_i18n": {"ru": ["А", "Б", "Е", "Ж"]},
                        "correct_answers_i18n": {"ru": ["А", "Е"]},
                        "duration_seconds": 45,
                        "points": 2,
                        "images_urls": [
                            "https://example.com/images/vowels-A.jpg",
                            "https://example.com/images/vowels-B.jpg",
                            "https://example.com/images/vowels-E.jpg",
                            "https://example.com/images/vowels-Zh.jpg"
                        ]
                    },
                    {
                        "type": "open",
                        "text_i18n": {"ru": "Столица Казахстана?"},
                        "correct_answers_i18n": {"ru": ["Астана", "Нур-Султан"]},
                        "duration_seconds": 60,
                        "points": 1
                    }
                ]
            }
        }
    )

class QuizQuestionsBulkOut(BaseModel):
    created: int
    ids: List[int]

class QuizQuestionLocalizedOut(BaseModel):
    id: int
    type: QuestionType
    text: str
    options: List[str] = []
    duration_seconds: Optional[int] = None
    points: int
    images_urls: List[str] = []


class UserLeaderboardOut(BaseModel):
    telegram_id: int
    nickname: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    points: int

class QuizProgressOut(BaseModel):
    total: int
    answered: int
    remaining: int
    unanswered_ids: List[int]

class AttachUrlsIn(BaseModel):
    """Модель для прикрепления внешних URL изображений к вопросу."""
    urls: List[AnyUrl] = Field(
        ...,
        example=[
            "https://example.com/images/question1.png",
            "https://cdn.site.com/pictures/diagram.jpg"
        ],
        description="Список абсолютных URL изображений, которые нужно прикрепить к вопросу."
    )