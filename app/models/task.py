import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Task(Base):
    """태스크 이력 테이블."""

    __tablename__ = "tasks"

    taskId: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    accountId: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.accountId"))
    request: Mapped[str] = mapped_column(Text, default="")
    requiredAbilities: Mapped[dict] = mapped_column(JSON, default=list)  # 능력치 ID 배열
    requiredDate: Mapped[int] = mapped_column(Integer, default=0)
    requiredElo: Mapped[int] = mapped_column(Integer, default=0)
    requiredCost: Mapped[int] = mapped_column(Integer, default=0)
    elo: Mapped[int] = mapped_column(Integer, default=1000)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending, matched, completed, failed

    account = relationship("Account", back_populates="tasks")
