import enum
from typing import Dict, List, Optional

from sqlalchemy import String, Integer, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.common.db import Base

class QuestionType(str, enum.Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    OPEN = "open"

class Quiz(Base):
    __tablename__ = "quizes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ⬇️ вместо одного text — словарь локалей
    # { "ru": "Столица Казахстана?", "kk": "Қазақстан астанасы?" }
    text_i18n: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)

    # ⬇️ тип вопроса — ЯВНО
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)

    # ⬇️ варианты ответов тоже по локали (для OPEN можно пустыми списками)
    # { "ru": ["А", "Б", "В"], "kk": ["А", "Б", "В"] }
    options_i18n: Mapped[Dict[str, List[str]]] = mapped_column(JSON, default=dict)

    # ⬇️ правильные ответы по локали
    # single/multiple: тексты из options соответствующей локали
    # open: список допустимых строк (синонимы/варианты) для этой локали
    # { "ru": ["Астана", "Нур-Султан"], "kk": ["Астана"] }  # для OPEN
    correct_answers_i18n: Mapped[Dict[str, List[str]]] = mapped_column(JSON, default=dict)

    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=60, nullable=True)

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizes.id", ondelete="CASCADE"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=1)

class QuizUserAnswer(Base):
    __tablename__ = "quiz_user_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id", ondelete="CASCADE"))
    # сохраняем то, что пришло (для single — список из одного, для open — список/одна строка)
    answers: Mapped[List[str]] = mapped_column(JSON, default=list)

    # ⬇️ фиксируем локаль, на которой отвечал пользователь
    locale: Mapped[str] = mapped_column(String(10), default="ru")

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizes.id", ondelete="CASCADE"))
