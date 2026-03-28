"""계정 검색 서비스 — 키워드 검색 + 벡터 유사도 검색."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.services import gemini
from app.services import qdrant as qdrantService

KEYWORD_MAX_RESULTS = 1000
VECTOR_MAX_RESULTS = 200
VECTOR_MIN_SIMILARITY = 0.7


async def searchByKeyword(db: AsyncSession, query: str, limit: int = KEYWORD_MAX_RESULTS) -> list[dict]:
    """키워드 검색 — abilityText에서 LIKE 패턴 매칭.
    쿼리를 공백 기준으로 분리해 각 키워드가 포함된 계정을 찾고,
    매칭된 키워드 수 비율을 similarity로 반환.
    """
    keywords = [kw.strip() for kw in query.split() if kw.strip()]
    if not keywords:
        return []

    # 모든 계정 중 하나라도 키워드가 매칭되는 계정 수집
    stmt = select(Account)
    accounts = (await db.execute(stmt)).scalars().all()

    scored = []
    for account in accounts:
        text = (account.abilityText or "").lower()
        matchCount = sum(1 for kw in keywords if kw.lower() in text)
        if matchCount > 0:
            similarity = round(matchCount / len(keywords), 4)
            scored.append({"accountId": account.accountId, "similarity": similarity})

    # 유사도 내림차순 정렬
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:min(limit, KEYWORD_MAX_RESULTS)]


async def searchByVector(db: AsyncSession, query: str, limit: int = VECTOR_MAX_RESULTS) -> list[dict]:
    """벡터 유사도 검색 — 쿼리를 임베딩하여 Qdrant에서 유사한 능력치를 찾고,
    동일 계정의 최고 유사도를 집계하여 계정별로 정렬.
    """
    vector = await gemini.embedText(query)

    hits = qdrantService.searchAbilities(vector, limit=limit * 3)
    if not hits:
        return []

    # 계정별 최고 유사도 집계 (최소 유사도 기준 이상만)
    accountBest: dict[str, float] = {}
    for hit in hits:
        accountId = hit["accountId"]
        similarity = hit["similarity"]
        if similarity < VECTOR_MIN_SIMILARITY:
            continue
        if accountId not in accountBest or similarity > accountBest[accountId]:
            accountBest[accountId] = similarity

    # 유사도 내림차순 정렬
    results = [
        {"accountId": aid, "similarity": round(sim, 4)}
        for aid, sim in accountBest.items()
    ]
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:min(limit, VECTOR_MAX_RESULTS)]
