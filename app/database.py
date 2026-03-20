from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.databaseUrl, echo=False)
asyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 베이스 클래스."""
    pass


async def getDb():
    """FastAPI 의존성 — DB 세션 제공."""
    async with asyncSessionLocal() as session:
        yield session


async def initDb():
    """테이블 자동 생성."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
