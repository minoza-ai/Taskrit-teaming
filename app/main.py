"""Taskrit TeamingOn Engine — FastAPI 엔트리 포인트."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import initDb
from app.routers import account, ability, task, search

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 DB 테이블 생성."""
    await initDb()
    yield

app = FastAPI(
    title="Taskrit TeamingOn Engine",
    description="능력치 벡터화 + 하이브리드 매칭 마이크로서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(account.router)
app.include_router(ability.router)
app.include_router(task.router)
app.include_router(search.router)

@app.get("/")
async def root():
    return {"service": "TeamingOn Engine", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=3002, reload=True)

