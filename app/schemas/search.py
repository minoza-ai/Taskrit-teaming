from pydantic import BaseModel


class SearchRequest(BaseModel):
    """계정 검색 요청."""

    query: str
    mode: str = "keyword"  # keyword, vector
    limit: int = 20


class SearchResult(BaseModel):
    """검색 결과 단일 항목."""

    accountId: str
    similarity: float


class SearchResponse(BaseModel):
    """검색 응답."""

    query: str
    mode: str
    results: list[SearchResult]
