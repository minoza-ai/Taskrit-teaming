"""계정 검색 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import getDb
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services import search as searchService

router = APIRouter(tags=["Search"])


@router.post("/Search", response_model=SearchResponse)
async def searchAccounts(body: SearchRequest, db: AsyncSession = Depends(getDb)):
    """계정 검색 — 키워드 또는 벡터 유사도 모드."""
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    if body.mode not in ("keyword", "vector"):
        raise HTTPException(status_code=422, detail="Mode must be 'keyword' or 'vector'")

    try:
        if body.mode == "keyword":
            results = await searchService.searchByKeyword(db, body.query, body.limit)
        else:
            results = await searchService.searchByVector(db, body.query, body.limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    return SearchResponse(
        query=body.query,
        mode=body.mode,
        results=[SearchResult(**r) for r in results],
    )
