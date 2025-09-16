from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from app.common.db import Base
from app.events.models import event_players

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    points: Mapped[int] = mapped_column(default=0)

    # ивенты, которые он создал
    created_events: Mapped[list["Event"]] = relationship(
    back_populates="creator",
    cascade="all, delete-orphan",
    lazy="selectin"
)

    # ивенты, где он участник
    events: Mapped[list["Event"]] = relationship(
    secondary="event_players",   # таблица связки
    back_populates="players",
    lazy="selectin"
)
