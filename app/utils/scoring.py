"""스코어링 유틸리티 — 가중치 상수 및 정규화 함수."""

from datetime import datetime

# 계정 타입별 가중치
WEIGHTS = {
    "human": {"vector": 0.30, "keyword": 0.30, "elo": 0.30, "cost": 0.05, "newBonus": 0.05},
    "agent": {"vector": 0.35, "keyword": 0.35, "elo": 0.15, "cost": 0.10, "newBonus": 0.05},
    "robot": {"vector": 0.35, "keyword": 0.35, "elo": 0.15, "cost": 0.10, "newBonus": 0.05},
    "asset": {"vector": 0.30, "keyword": 0.30, "elo": 0.15, "cost": 0.20, "newBonus": 0.05},
}

NEW_BONUS_DAYS = 30  # 신규 보너스 적용 기간 (일)


def normalizeValue(val: float, minVal: float, maxVal: float, reverse: bool = False) -> float:
    """후보군 내에서 0~1로 Min-Max 정규화. reverse=True이면 값이 작을수록 1.0에 가까워짐 (비용 등)."""
    if maxVal <= minVal:
        return 1.0  # 모두 동일하면 일괄적으로 최고점
    norm = (val - minVal) / (maxVal - minVal)
    norm = max(0.0, min(1.0, norm))
    return 1.0 - norm if reverse else norm

def calcNewBonus(joinDate: datetime) -> float:
    """신규 가입 보너스 (가입 30일 이내 시 감쇠 보너스)."""
    daysSinceJoin = (datetime.utcnow() - joinDate).days
    if daysSinceJoin >= NEW_BONUS_DAYS:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (daysSinceJoin / NEW_BONUS_DAYS)))

def calcHybridScore(
    accountType: str,
    normVectorSim: float,
    normKeywordSim: float,
    normElo: float,
    normCost: float,
    joinDate: datetime,
) -> float:
    """하이브리드 리랭킹 점수 계산. 
    가중치와 별개로 공정한 범위(0~1) 내에서 동작하도록 정규화된 값들을 사용.
    """
    w = WEIGHTS.get(accountType, WEIGHTS["human"])
    score = (
        w["vector"] * normVectorSim
        + w["keyword"] * normKeywordSim
        + w["elo"] * normElo
        + w["cost"] * normCost
        + w["newBonus"] * calcNewBonus(joinDate)
    )
    return max(0.0, score)
