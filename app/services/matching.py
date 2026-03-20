"""하이브리드 매칭 엔진 — 3단계 추출."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.ability import Ability
from app.services import gemini
from app.services import qdrant as qdrantService
from app.utils.scoring import calcHybridScore

async def matchForTask(
    db: AsyncSession,
    requiredSkills: list[str],
    requiredElo: int = 0,
    requiredCost: int = 0,
    requireHuman: bool = False,
) -> list[dict]:
    """태스크에 필요한 능력치별 매칭 결과 반환.
    Returns:
        [{"requiredAbility": str, "candidates": [...]}, ...]
    """
    # 배치 임베딩 — 모든 능력치를 1회 API 호출로 벡터화
    vectors = await gemini.embedTexts(requiredSkills)

    results = []
    for skill, vector in zip(requiredSkills, vectors):
        # 2차: 벡터 유사도 검색
        hits = qdrantService.searchAbilities(vector, limit=30)
        if not hits:
            results.append({"requiredAbility": skill, "candidates": []})
            continue

        # 후보 계정 정보 로드 + 1차 하드 필터
        candidates = []
        for hit in hits:
            account = await db.get(Account, hit["accountId"])
            if not account:
                continue

            # 1차: 하드 리미트 필터
            if not account.availability:
                continue
            if requiredElo > 0 and account.elo < requiredElo:
                continue
            if requiredCost > 0 and account.cost > requiredCost:
                continue

            # 능력치 텍스트 조회
            ability = await db.get(Ability, hit["abilityId"])
            abilityText = ability.abilityText if ability else ""

            # 에셋이면 능동 계정 연결 탐색
            linkedAssetId = None
            if account.type == "asset":
                linkedAssetId = await _findOperator(db, account.accountId, requiredElo, requiredCost)

            candidates.append({
                "accountId": account.accountId,
                "accountType": account.type,
                "abilityText": abilityText,
                "similarity": hit["similarity"],
                "elo": account.elo,
                "cost": account.cost,
                "joinDate": account.joinDate,
                "linkedAssetId": linkedAssetId,
            })

        # 3차: 하이브리드 리랭킹
        maxCost = max((c["cost"] for c in candidates), default=1)
        for c in candidates:
            c["score"] = calcHybridScore(
                accountType=c["accountType"],
                similarity=c["similarity"],
                elo=c["elo"],
                cost=c["cost"],
                maxCost=maxCost,
                joinDate=c["joinDate"],
            )

        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 응답 형태로 정리
        results.append({
            "requiredAbility": skill,
            "candidates": [
                {
                    "accountId": c["accountId"],
                    "accountType": c["accountType"],
                    "abilityText": c["abilityText"],
                    "similarity": round(c["similarity"], 4),
                    "score": round(c["score"], 4),
                    "linkedAssetId": c.get("linkedAssetId"),
                }
                for c in candidates[:10]  # 상위 10개
            ],
        })

    return results

async def _findOperator(db: AsyncSession, assetAccountId: str, requiredElo: int, requiredCost: int) -> str | None:
    """에셋의 요구 능력치를 충족하는 능동 계정을 탐색."""
    from app.models.requirement import Requirement

    reqs = (await db.execute(
        select(Requirement).where(Requirement.accountId == assetAccountId)
    )).scalars().all()

    if not reqs:
        return None

    # 요구 능력치를 배치 임베딩
    reqTexts = [req.abilityText for req in reqs]
    reqVectors = await gemini.embedTexts(reqTexts)

    for vector in reqVectors:
        hits = qdrantService.searchAbilities(vector, limit=5)
        for hit in hits:
            account = await db.get(Account, hit["accountId"])
            if not account or account.accountId == assetAccountId:
                continue
            if account.type == "asset":
                continue
            if not account.availability:
                continue
            if requiredElo > 0 and account.elo < requiredElo:
                continue
            if requiredCost > 0 and account.cost > requiredCost:
                continue
            return account.accountId

    return None
