"""스코어링 유틸리티 — 가중치 상수 및 정규화 함수."""

from datetime import datetime

# 계정 타입별 가중치 (W1=유사도, W2=elo, W3=비용효율, W4=신규보너스)
WEIGHTS = {
    "human": {"similarity": 0.25, "elo": 0.40, "cost": 0.20, "newBonus": 0.15},
    "agent": {"similarity": 0.45, "elo": 0.20, "cost": 0.20, "newBonus": 0.15},
    "robot": {"similarity": 0.45, "elo": 0.20, "cost": 0.20, "newBonus": 0.15},
    "asset": {"similarity": 0.20, "elo": 0.15, "cost": 0.45, "newBonus": 0.20},
}

NEW_BONUS_DAYS = 30  # 신규 보너스 적용 기간 (일)


def normalizeElo(elo: int, maxElo: int = 3000) -> float:
    """ELO를 0~1로 정규화."""
    return min(max(elo / maxElo, 0.0), 1.0)


def normalizeCostEfficiency(cost: int, maxCost: int) -> float:
    """단가 효율성 — 낮을수록 효율적 (0~1, 1이 가장 효율적)."""
    if maxCost <= 0:
        return 1.0
    return 1.0 - min(cost / maxCost, 1.0)


def calcNewBonus(joinDate: datetime) -> float:
    """신규 가입 보너스 (가입 30일 이내 시 감쇠 보너스)."""
    daysSinceJoin = (datetime.utcnow() - joinDate).days
    if daysSinceJoin >= NEW_BONUS_DAYS:
        return 0.0
    return 1.0 - (daysSinceJoin / NEW_BONUS_DAYS)


def calcHybridScore(
    accountType: str,
    similarity: float,
    elo: int,
    cost: int,
    maxCost: int,
    joinDate: datetime,
) -> float:
    """하이브리드 리랭킹 점수 계산."""
    w = WEIGHTS.get(accountType, WEIGHTS["human"])
    return (
        w["similarity"] * similarity
        + w["elo"] * normalizeElo(elo)
        + w["cost"] * normalizeCostEfficiency(cost, maxCost)
        + w["newBonus"] * calcNewBonus(joinDate)
    )
