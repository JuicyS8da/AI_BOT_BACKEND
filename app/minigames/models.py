import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.common.db import Base

class QuestionType(str, enum.Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    OPEN = "open"

class Minigame(Base):
    __tablename__ = "minigames"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)

class MinigameQuestion(Base):
    __tablename__ = "minigame_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(255), nullable=False)

    # список правильных ответов (["A"], ["A", "B"], или [])
    correct_answers: Mapped[list[str]] = mapped_column(JSON, default=list)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)

    minigame_id: Mapped[int] = mapped_column(ForeignKey("minigames.id"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=1)  # базовое кол-во очков


class MinigameUserAnswer(Base):
    __tablename__ = "minigame_user_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("minigame_questions.id", ondelete="CASCADE"))
    answer: Mapped[str] = mapped_column(String(255), nullable=False)

    minigame_id: Mapped[int] = mapped_column(ForeignKey("minigames.id", ondelete="CASCADE"))

