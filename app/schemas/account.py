from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AccountCreate(BaseModel):
    """계정 생성 요청."""
    accountId: str
    type: str  # human, agent, robot, asset
    abilityText: str
    cost: int = 0


class AccountUpdate(BaseModel):
    """계정 상태 수정 요청."""
    abilityText: Optional[str] = None
    availability: Optional[bool] = None
    cost: Optional[int] = None


class AccountResponse(BaseModel):
    """계정 응답."""
    accountId: str
    type: str
    elo: int
    abilityText: str
    availability: bool
    cost: int
    joinDate: datetime

    model_config = {"from_attributes": True}


class AccountComponents(BaseModel):
    """계정 구성요소 (능력치/요구 능력치 ID 목록)."""
    accountId: str
    abilityIds: list[str]
    requirementIds: list[str]
