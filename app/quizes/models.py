import enum

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
    description: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(255), nullable=False)

    # список правильных ответов (["A"], ["A", "B"], или [])
    correct_answers: Mapped[list[str]] = mapped_column(JSON, default=list)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)

    duration_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=True)

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizes.id", ondelete="CASCADE"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=1)  # базовое кол-во очков


class QuizUserAnswer(Base):
    __tablename__ = "quiz_user_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id", ondelete="CASCADE"))
    answers: Mapped[list[str]] = mapped_column(JSON, default=list)

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizes.id", ondelete="CASCADE"))

