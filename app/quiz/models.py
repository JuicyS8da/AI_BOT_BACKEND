from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base

class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan"
    )

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(255), nullable=False)

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    quiz: Mapped["Quiz"] = relationship(back_populates="questions")

    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)

    answers: Mapped[list["UserAnswer"]] = relationship(back_populates="question", cascade="all, delete-orphan")

class UserAnswer(Base):
    __tablename__ = "user_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)  # можно привязать к users.id, если есть таблица
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id", ondelete="CASCADE"))
    question: Mapped["QuizQuestion"] = relationship(back_populates="answers")