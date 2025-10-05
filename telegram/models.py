# app/users/models.py (или отдельный модуль)
from sqlalchemy import BigInteger, String, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

class ModStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_tid: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)     # telegram_id пользователя-заявителя
    admin_chat_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=ModStatus.pending.value, nullable=False)
