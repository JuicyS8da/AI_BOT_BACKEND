import enum
from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, ForeignKey, Column, Table, Integer

from app.common.db import Base

class EventStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    REGISTRATION = "registration"
    STARTED = "started"
    FINISHED = "finished"

event_players = Table(
    "event_players",
    Base.metadata,
    Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("user_telegram_id", ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True),
)

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="game_status"),
        default=EventStatus.NOT_STARTED,
        nullable=False
    )
    current_question_index: Mapped[int] = mapped_column(default=0, nullable=False)

    # создатель (как у вас было)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    creator = relationship("User", back_populates="created_events", lazy="selectin")

    # ВАЖНО: больше НЕТ 'questions'. Теперь связь с квизами:
    quizes: Mapped[List["Quiz"]] = relationship(
        "Quiz",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # игроки (many-to-many) как у вас было  
    players = relationship(
        "User",
        secondary="event_players",
        back_populates="events",
        lazy="selectin",
    )
    