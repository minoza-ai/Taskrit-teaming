"""Qdrant 벡터 스토어 서비스."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings

# 로컬 파일 Qdrant (서버 재시작 후에도 데이터 유지)
qdrant = QdrantClient(path="./qdrant_data")

ABILITY_COLLECTION = "abilities"
REQUIREMENT_COLLECTION = "requirements"
# 프로젝트 설명이 길거나 추상적일 때도 후보를 찾을 수 있도록 recall을 높인다.
# 에셋도 충분히 검색되도록 임계값을 낮춤
SIMILARITY_THRESHOLD = 0.25

def initCollections():
    """Qdrant 컬렉션 초기화."""
    for name in [ABILITY_COLLECTION, REQUIREMENT_COLLECTION]:
        if not qdrant.collection_exists(name):
            qdrant.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=settings.embeddingDim,
                    distance=Distance.COSINE,
                ),
            )

def upsertAbility(abilityId: str, accountId: str, vector: list[float]):
    """능력치 벡터 저장."""
    qdrant.upsert(
        collection_name=ABILITY_COLLECTION,
        points=[
            PointStruct(
                id=abilityId,
                vector=vector,
                payload={"accountId": accountId},
            )
        ],
    )

def upsertRequirement(requirementId: str, accountId: str, vector: list[float]):
    """요구 능력치 벡터 저장."""
    qdrant.upsert(
        collection_name=REQUIREMENT_COLLECTION,
        points=[
            PointStruct(
                id=requirementId,
                vector=vector,
                payload={"accountId": accountId},
            )
        ],
    )

def searchAbilities(vector: list[float], limit: int = 20) -> list[dict]:
    """능력치 벡터 유사도 검색 (일반 사용자/에이전트/로봇)."""
    results = qdrant.query_points(
        collection_name=ABILITY_COLLECTION,
        query=vector,
        limit=limit * 2,  # 더 많은 후보를 검색해 에셋도 충분히 포함
        score_threshold=SIMILARITY_THRESHOLD,
    ).points
    return [
        {
            "abilityId": str(hit.id),
            "accountId": hit.payload["accountId"],
            "similarity": hit.score,
        }
        for hit in results
    ]

def searchRequirements(vector: list[float], limit: int = 10) -> list[dict]:
    """요구 능력치 벡터 유사도 검색 (에셋의 요구 능력치 기반 검색)."""
    results = qdrant.query_points(
        collection_name=REQUIREMENT_COLLECTION,
        query=vector,
        limit=limit * 3,  # 에셋 검색을 위해 더 많은 후보를 수집
        score_threshold=SIMILARITY_THRESHOLD,
    ).points
    return [
        {
            "requirementId": str(hit.id),
            "accountId": hit.payload["accountId"],
            "similarity": hit.score,
        }
        for hit in results
    ]

def getRequirementVector(requirementId: str) -> list[float] | None:
    """ID로 요구 능력치 벡터(임베딩) 즉시 조회."""
    try:
        results = qdrant.retrieve(
            collection_name=REQUIREMENT_COLLECTION,
            ids=[requirementId],
            with_vectors=True
        )
        if results and results[0].vector:
            return results[0].vector
    except Exception:
        pass
    return None

def deleteByAccount(accountId: str):
    """계정 삭제 시 벡터도 제거."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    accountFilter = Filter(
        must=[FieldCondition(key="accountId", match=MatchValue(value=accountId))]
    )
    for collection in [ABILITY_COLLECTION, REQUIREMENT_COLLECTION]:
        qdrant.delete(collection_name=collection, points_selector=accountFilter)

# 서버 시작 시 컬렉션 초기화
initCollections()
