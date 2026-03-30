"""하이브리드 매칭 엔진 — 3단계 추출."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import gemini
from app.services import qdrant as qdrantService
from app.utils.scoring import calcHybridScore, normalizeValue

async def matchForTask(db: AsyncIOMotorDatabase, requiredSkills: list[str], requiredElo: int = 0, requiredCost: int = 0, requireHuman: bool = False) -> list[dict]:
    """태스크에 필요한 능력치별 매칭 결과 반환.
    Returns:
        [{"requiredAbility": str, "candidates": [...]}, ...]
    """
    # 배치 임베딩 — 모든 능력치를 1회 API 호출로 벡터화
    vectors = await gemini.embedTexts(requiredSkills)

    results = []
    for skill, vector in zip(requiredSkills, vectors):
        # 2차: 벡터 유사도 검색 — 능력치(일반) + 요구능력치(에셋)
        abilityHits = qdrantService.searchAbilities(vector, limit=30)
        requirementHits = qdrantService.searchRequirements(vector, limit=30)  # 에셋 검색 강화

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
            account = await db.accounts.find_one({"accountId": hit["accountId"]}, {"_id": 0})
            if not account:
                continue

            # 1차: 하드 리미트 필터
            if not account.get("availability", True):
                continue
            accountElo = int(account.get("elo", 1000))
            if requiredElo > 0 and accountElo < requiredElo:
                continue

            # 능력치 텍스트 조회
            abilityText = ""
            if hit["source"] == "ability" and hit["abilityId"]:
                ability = await db.abilities.find_one({"abilityId": hit["abilityId"]}, {"_id": 0, "abilityText": 1})
                abilityText = ability.get("abilityText", "") if ability else ""
            elif hit["source"] == "requirement" and hit["requirementId"]:
                requirement = await db.requirements.find_one({"requirementId": hit["requirementId"]}, {"_id": 0, "abilityText": 1})
                abilityText = requirement.get("abilityText", "") if requirement else ""

            if not abilityText:
                abilityText = account.get("abilityText", "")

            # 에셋이면 능동 계정 연결 탐색
            linkedAssetId = None
            operatorCost = 0
            accountType = account.get("type", "")
            if accountType == "asset":
                linkedAssetId, operatorCost = await _findOperator(db, account["accountId"], requiredElo, requiredCost)

            totalCost = int(account.get("cost", 0)) + operatorCost
            
            # 합산된 총 비용으로 하드 리미트 재검증
            if requiredCost > 0 and totalCost > requiredCost:
                continue

            similarity = hit["similarity"]
            # 요구 능력치 기반으로 발견된 에셋은 소폭 가산해 후보로 노출되기 쉽게 조정
            if hit["source"] == "requirement" and accountType == "asset":
                similarity = min(1.0, similarity + 0.12)  # 0.07 → 0.12로 상향 (에셋 가산점 증대)

            candidate = {
                "accountId": account["accountId"],
                "accountType": accountType,
                "abilityText": abilityText,
                "similarity": similarity,
                "elo": accountElo,
                "cost": totalCost,
                "joinDate": account.get("joinDate"),
                "linkedAssetId": linkedAssetId,
            }

            prev = candidateByAccount.get(account["accountId"])
            if not prev or candidate["similarity"] > prev["similarity"]:
                candidateByAccount[account["accountId"]] = candidate

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

async def _findOperator(db: AsyncIOMotorDatabase, assetAccountId: str, requiredElo: int, requiredCost: int) -> tuple[str | None, int]:
    """에셋의 요구 능력치를 충족하는 능동 계정을 탐색. 반환치: (조종사ID, 조종사비용)"""
    reqs = await db.requirements.find({"accountId": assetAccountId}, {"_id": 0, "requirementId": 1}).to_list(length=100)

    if not reqs:
        return None, 0

    for req in reqs:
        vector = qdrantService.getRequirementVector(req["requirementId"])
        if not vector:
            continue
            
        hits = qdrantService.searchAbilities(vector, limit=5)
        for hit in hits:
            account = await db.accounts.find_one({"accountId": hit["accountId"]}, {"_id": 0})
            if not account or account["accountId"] == assetAccountId or account.get("type") == "asset":
                continue
            if not account.get("availability", True):
                continue
            accountElo = int(account.get("elo", 1000))
            accountCost = int(account.get("cost", 0))
            if requiredElo > 0 and accountElo < requiredElo:
                continue
            if requiredCost > 0 and accountCost > requiredCost:
                continue
            return account["accountId"], accountCost

    return None, 0