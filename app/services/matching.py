"""하이브리드 매칭 엔진 — 3단계 추출."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.ability import Ability
from app.models.requirement import Requirement
from app.services import gemini
from app.services import qdrant as qdrantService
from app.utils.scoring import calcHybridScore, normalizeValue

async def matchForTask(db: AsyncSession, requiredSkills: list[str], requiredElo: int = 0, requiredCost: int = 0, requireHuman: bool = False) -> list[dict]:
    """태스크에 필요한 능력치별 매칭 결과 반환.
    Returns:
        [{"requiredAbility": str, "candidates": [...]}, ...]
    """
    # 배치 임베딩 — 모든 능력치를 1회 API 호출로 벡터화
    vectors = await gemini.embedTexts(requiredSkills)

    results = []
    for skill, vector in zip(requiredSkills, vectors):
        # 2차: 벡터 유사도 검색
        abilityHits = qdrantService.searchAbilities(vector, limit=30)
        requirementHits = qdrantService.searchRequirements(vector, limit=20)

        mergedHits = [
            {
                "source": "ability",
                "abilityId": hit["abilityId"],
                "requirementId": None,
                "accountId": hit["accountId"],
                "similarity": hit["similarity"],
            }
            for hit in abilityHits
        ] + [
            {
                "source": "requirement",
                "abilityId": None,
                "requirementId": hit["requirementId"],
                "accountId": hit["accountId"],
                "similarity": hit["similarity"],
            }
            for hit in requirementHits
        ]

        if not mergedHits:
            results.append({"requiredAbility": skill, "candidates": []})
            continue

        # 후보 계정 정보 로드 + 1차 하드 필터
        candidateByAccount: dict[str, dict] = {}
        for hit in mergedHits:
            account = await db.get(Account, hit["accountId"])
            if not account:
                continue

            # 1차: 하드 리미트 필터
            if not account.availability:
                continue
            if requiredElo > 0 and account.elo < requiredElo:
                continue

            # 능력치 텍스트 조회
            abilityText = ""
            if hit["source"] == "ability" and hit["abilityId"]:
                ability = await db.get(Ability, hit["abilityId"])
                abilityText = ability.abilityText if ability else ""
            elif hit["source"] == "requirement" and hit["requirementId"]:
                requirement = await db.get(Requirement, hit["requirementId"])
                abilityText = requirement.abilityText if requirement else ""

            if not abilityText:
                abilityText = account.abilityText

            # 에셋이면 능동 계정 연결 탐색
            linkedAssetId = None
            operatorCost = 0
            if account.type == "asset":
                linkedAssetId, operatorCost = await _findOperator(db, account.accountId, requiredElo, requiredCost)

            totalCost = account.cost + operatorCost
            
            # 합산된 총 비용으로 하드 리미트 재검증
            if requiredCost > 0 and totalCost > requiredCost:
                continue

            similarity = hit["similarity"]
            # 요구 능력치 기반으로 발견된 에셋은 소폭 가산해 후보로 노출되기 쉽게 조정
            if hit["source"] == "requirement" and account.type == "asset":
                similarity = min(1.0, similarity + 0.07)

            candidate = {
                "accountId": account.accountId,
                "accountType": account.type,
                "abilityText": abilityText,
                "similarity": similarity,
                "elo": account.elo,
                "cost": totalCost,
                "joinDate": account.joinDate,
                "linkedAssetId": linkedAssetId,
            }

            prev = candidateByAccount.get(account.accountId)
            if not prev or candidate["similarity"] > prev["similarity"]:
                candidateByAccount[account.accountId] = candidate

        candidates = list(candidateByAccount.values())

        # 3차: 하이브리드 리랭킹
        if candidates:
            minSim = min(c["similarity"] for c in candidates)
            maxSim = max(c["similarity"] for c in candidates)
            minElo = min(c["elo"] for c in candidates)
            maxElo = max(c["elo"] for c in candidates)
            minCost = min(c["cost"] for c in candidates)
            maxCost = max(c["cost"] for c in candidates)
        else:
            minSim = maxSim = minElo = maxElo = minCost = maxCost = 0

        for c in candidates:
            normSim = normalizeValue(c["similarity"], minSim, maxSim)
            normElo = normalizeValue(c["elo"], minElo, maxElo)
            normCost = normalizeValue(c["cost"], minCost, maxCost, reverse=True)

            score = calcHybridScore(
                accountType=c["accountType"],
                normSimilarity=normSim,
                normElo=normElo,
                normCost=normCost,
                joinDate=c["joinDate"],
            )

            # requireHuman이 True일 때 인간 계정에게 필수 배정에 따른 압도적 가산점 부여
            if requireHuman and c["accountType"] == "human":
                score += 10.0

            c["score"] = score

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

async def _findOperator(db: AsyncSession, assetAccountId: str, requiredElo: int, requiredCost: int) -> tuple[str | None, int]:
    """에셋의 요구 능력치를 충족하는 능동 계정을 탐색. 반환치: (조종사ID, 조종사비용)"""
    from app.models.requirement import Requirement

    reqs = (await db.execute(
        select(Requirement).where(Requirement.accountId == assetAccountId)
    )).scalars().all()

    if not reqs:
        return None, 0

    for req in reqs:
        vector = qdrantService.getRequirementVector(req.requirementId)
        if not vector:
            continue
            
        hits = qdrantService.searchAbilities(vector, limit=5)
        for hit in hits:
            account = await db.get(Account, hit["accountId"])
            if not account or account.accountId == assetAccountId or account.type == "asset":
                continue
            if not account.availability:
                continue
            if requiredElo > 0 and account.elo < requiredElo:
                continue
            if requiredCost > 0 and account.cost > requiredCost:
                continue
            return account.accountId, account.cost

    return None, 0