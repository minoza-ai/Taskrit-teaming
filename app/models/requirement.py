import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Requirement(Base):
    """요구 능력치 테이블 (에셋 구동에 필요한 조건, N:1 with accounts)."""
    
    __tablename__ = "requirements"

    requirementId: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    accountId: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.accountId"))
    abilityText: Mapped[str] = mapped_column(Text, default="")

    # 벡터 임베딩은 Qdrant에 저장
    account = relationship("Account", back_populates="requirements")
