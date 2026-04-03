from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def getDb():
    """FastAPI 의존성 — MongoDB 데이터베이스 객체 제공."""
    if _db is None:
        await initDb()
    if _db is None:
        raise RuntimeError("MongoDB is not initialized")
    yield _db


async def initDb():
    """MongoDB 연결 및 컬렉션 인덱스 초기화."""
    global _client, _db
    if _db is not None:
        return

    _client = AsyncIOMotorClient(settings.mongoUri)
    _db = _client[settings.mongoDbName]


    await _db.teaming.create_index([("user_uuid", ASCENDING)], unique=True)
    await _db.teaming.create_index([("type", ASCENDING)])
    await _db.teaming.create_index([("availability", ASCENDING)])
    await _db.abilities.create_index([("abilityId", ASCENDING)], unique=True)
    await _db.abilities.create_index([("user_uuid", ASCENDING)])
    await _db.requirements.create_index([("requirementId", ASCENDING)], unique=True)
    await _db.requirements.create_index([("user_uuid", ASCENDING)])
    await _db.tasks.create_index([("taskId", ASCENDING)], unique=True)
    await _db.tasks.create_index([("accountId", ASCENDING)])
    await _db.tasks.create_index([("status", ASCENDING)])


async def closeDb():
    """MongoDB 연결 종료."""
    global _client, _db
    if _client is None:
        return
    _client.close()
    _client = None
    _db = None
