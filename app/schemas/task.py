from typing import Optional

from pydantic import BaseModel

class TaskCreate(BaseModel):
    """태스크 생성 요청."""

    accountId: str
    request: str
    requiredDate: int = 0
    requiredElo: int = 0
    requiredCost: int = 0
    requireHuman: bool = False  # 인간 계정 1개 이상 포함 제한
    maxCost: int = 0  # 단가 상한

class TaskResponse(BaseModel):
    """태스크 응답."""

    taskId: str
    accountId: str
    request: str
    requiredAbilities: list
    requiredDate: int
    requiredElo: int
    requiredCost: int
    elo: int
    status: str

    model_config = {"from_attributes": True}

class TaskStatusUpdate(BaseModel):
    """태스크 상태 변경 요청."""

    status: str  # completed, failed

class MatchCandidate(BaseModel):
    """매칭 후보 단일 항목."""

    accountId: str
    accountType: str
    abilityText: str
    similarity: float
    score: float
    linkedAssetId: Optional[str] = None  # 에셋에 연결된 능동 계정

class MatchResult(BaseModel):
    """매칭 결과."""
    
    taskId: str
    requiredAbility: str
    candidates: list[MatchCandidate]
