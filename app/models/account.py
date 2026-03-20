import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Account(Base):
    """계정 마스터 테이블."""

    __tablename__ = "accounts"

    accountId: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(16))  # human, agent, robot, asset
    elo: Mapped[int] = mapped_column(Integer, default=1000)
    abilityText: Mapped[str] = mapped_column(Text, default="")
    availability: Mapped[bool] = mapped_column(Boolean, default=True)
    cost: Mapped[int] = mapped_column(Integer, default=0)
    joinDate: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # relationships
    abilities = relationship("Ability", back_populates="account", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="account", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="account", cascade="all, delete-orphan")
