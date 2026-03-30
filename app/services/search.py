"""계정 검색 서비스 — 키워드 검색 + 벡터 유사도 검색."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import gemini
from app.services import qdrant as qdrantService

KEYWORD_MAX_RESULTS = 1000
VECTOR_MAX_RESULTS = 200
VECTOR_MIN_SIMILARITY = 0.7


async def searchByKeyword(db: AsyncIOMotorDatabase, query: str, limit: int = KEYWORD_MAX_RESULTS) -> list[dict]:
    """키워드 검색 — users.profile_bio 기반 부분 매칭.
    쿼리를 공백 기준으로 분리해 각 키워드가 포함된 프로필을 찾고,
    매칭된 키워드 수 비율을 similarity로 반환.
    """
    keywords = [kw.strip() for kw in query.split() if kw.strip()]
    if not keywords:
        return []

    teamingDocs = await db.teaming.find(
        {"availability": True},
        {"_id": 0, "user_uuid": 1},
    ).to_list(length=100000)
    userUuids = [doc["user_uuid"] for doc in teamingDocs if isinstance(doc.get("user_uuid"), str)]
    if not userUuids:
        return []

    scored = []
    cursor = db.users.find(
        {
            "user_uuid": {"$in": userUuids},
            "deleted_at": None,
            "profile_bio": {"$type": "string", "$ne": ""},
        },
        {"_id": 0, "user_uuid": 1, "profile_bio": 1},
    )
    async for user in cursor:
        text = (user.get("profile_bio") or "").lower()
        matchCount = sum(1 for kw in keywords if kw.lower() in text)
        if matchCount > 0:
            similarity = round(matchCount / len(keywords), 4)
            scored.append({"accountId": user["user_uuid"], "similarity": similarity})

    # 유사도 내림차순 정렬
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:min(limit, KEYWORD_MAX_RESULTS)]


async def searchByVector(db: AsyncIOMotorDatabase, query: str, limit: int = VECTOR_MAX_RESULTS) -> list[dict]:
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
        accountId = hit["user_uuid"]
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
