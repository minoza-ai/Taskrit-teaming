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
        await conn.run_sync(_ensureAccountColumnsSync)


def _ensureAccountColumnsSync(syncConn):
    """기존 SQLite DB에 누락된 accounts 컬럼을 안전하게 추가."""
    if syncConn.dialect.name != "sqlite":
        return

    tableExists = syncConn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
    ).fetchone()

    if not tableExists:
        return

    columns = {
        row[1]
        for row in syncConn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()
    }

    if "userId" not in columns:
        syncConn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN userId VARCHAR(64)")

    if "nickname" not in columns:
        syncConn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN nickname VARCHAR(128)")
