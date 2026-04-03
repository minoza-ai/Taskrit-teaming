"""계정 비즈니스 로직."""

import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import gemini
from app.services import qdrant as qdrantService


def _toAccountResponse(doc: dict) -> dict:
    return {
        "accountId": doc["user_uuid"],
        "type": doc.get("type", "human"),
        "elo": int(doc.get("elo", 1000)),
        "availability": bool(doc.get("availability", True)),
        "cost": int(doc.get("cost", 0)),
    }


async def _getUserProfileBio(db: AsyncIOMotorDatabase, userUuid: str) -> str:
    user = await db.users.find_one(
        {"user_uuid": userUuid, "deleted_at": None},
        {"_id": 0, "profile_bio": 1},
    )
    if not user:
        return ""
    profileBio = user.get("profile_bio")
    if not isinstance(profileBio, str):
        return ""
    return profileBio.strip()


async def _rebuildVectors(db: AsyncIOMotorDatabase, userUuid: str, accountType: str, sourceText: str) -> None:
    await db.abilities.delete_many({"$or": [{"user_uuid": userUuid}, {"accountId": userUuid}]})
    await db.requirements.delete_many({"$or": [{"user_uuid": userUuid}, {"accountId": userUuid}]})
    qdrantService.deleteByUserUuid(userUuid)

    if not sourceText.strip():
        return

    skills = await gemini.decomposeAbilities(sourceText)
    if skills:
        texts_to_embed = [s.get("abilityText", "") for s in skills]
        vectors = await gemini.embedTexts(texts_to_embed)
        for skillObj, vector in zip(skills, vectors):
            abilityId = str(uuid.uuid4())
            doc = {
                "abilityId": abilityId,
                "user_uuid": userUuid,
                "abilityText": skillObj.get("abilityText", ""),
                "domain": skillObj.get("domain"),
                "job": skillObj.get("job"),
                "proficiency": skillObj.get("proficiency"),
                "techStack": skillObj.get("techStack", []),
                "legacyDegree": skillObj.get("legacyDegree"),
            }
            await db.abilities.insert_one(doc)
            qdrantService.upsertAbility(abilityId, userUuid, vector)

    if accountType == "asset":
        reqs = await gemini.decomposeRequirements(sourceText)
        if reqs:
            reqs = reqs[:1]
            texts_to_embed = [r.get("abilityText", "") for r in reqs]
            reqVectors = await gemini.embedTexts(texts_to_embed)
            for reqObj, vector in zip(reqs, reqVectors):
                requirementId = str(uuid.uuid4())
                doc = {
                    "requirementId": requirementId,
                    "user_uuid": userUuid,
                    "abilityText": reqObj.get("abilityText", ""),
                    "domain": reqObj.get("domain"),
                    "job": reqObj.get("job"),
                    "proficiency": reqObj.get("proficiency"),
                    "techStack": reqObj.get("techStack", []),
                    "legacyDegree": reqObj.get("legacyDegree"),
                }
                await db.requirements.insert_one(doc)
                qdrantService.upsertRequirement(requirementId, userUuid, vector)

async def createAccount(
    db: AsyncIOMotorDatabase,
    accountId: str,
    userId: str | None,
    nickname: str | None,
    accountType: str,
    abilityText: str,
    cost: int = 0,
    skipAi: bool = False,
) -> dict:
    """계정 생성 — teaming 컬렉션(요약 정보) + 벡터 인덱스 생성."""
    userUuid = accountId
    del userId, nickname

    teamingDoc = {
        "user_uuid": userUuid,
        "type": accountType,
        "elo": 1000,
        "availability": True,
        "cost": cost,
    }
    await db.teaming.insert_one(teamingDoc)

    if not skipAi:
        profileBio = await _getUserProfileBio(db, userUuid) if accountType == "human" else ""
        sourceText = profileBio if profileBio else abilityText
        await _rebuildVectors(db, userUuid, accountType, sourceText)

    created = await db.teaming.find_one({"user_uuid": userUuid}, {"_id": 0})
    if not created:
        raise RuntimeError("Failed to create teaming document")
    return _toAccountResponse(created)


async def deleteAccount(db: AsyncIOMotorDatabase, accountId: str) -> bool:
    """계정 삭제."""
    if not await db.teaming.find_one({"user_uuid": accountId}, {"_id": 0}):
        return False

    qdrantService.deleteByUserUuid(accountId)
    await db.teaming.delete_one({"user_uuid": accountId})
    await db.abilities.delete_many({"$or": [{"user_uuid": accountId}, {"accountId": accountId}]})
    await db.requirements.delete_many({"$or": [{"user_uuid": accountId}, {"accountId": accountId}]})
    await db.tasks.delete_many({"accountId": accountId})
    return True


async def getAccount(db: AsyncIOMotorDatabase, accountId: str) -> dict | None:
    """계정 조회."""
    doc = await db.teaming.find_one({"user_uuid": accountId}, {"_id": 0})
    return _toAccountResponse(doc) if doc else None


async def updateAccount(
    db: AsyncIOMotorDatabase,
    accountId: str,
    abilityText: str | None,
    userId: str | None,
    nickname: str | None,
    availability: bool | None,
    cost: int | None,
    skipAi: bool = False,
) -> dict | None:
    """계정 상태 수정."""
    doc = await db.teaming.find_one({"user_uuid": accountId}, {"_id": 0})
    if not doc:
        return None

    setDoc: dict = {}
    if availability is not None:
        setDoc["availability"] = availability
    if cost is not None:
        setDoc["cost"] = cost
    del userId, nickname

    if setDoc:
        await db.teaming.update_one({"user_uuid": accountId}, {"$set": setDoc})

    if not skipAi:
        accountType = doc.get("type", "human")
        if accountType == "human":
            hasAbility = await db.abilities.find_one({"user_uuid": accountId}, {"_id": 1})
            if not hasAbility:
                sourceText = await _getUserProfileBio(db, accountId)
                if not sourceText and abilityText:
                    sourceText = abilityText.strip()
                await _rebuildVectors(db, accountId, accountType, sourceText)
        elif abilityText is not None:
            await _rebuildVectors(db, accountId, accountType, abilityText)

    updated = await db.teaming.find_one({"user_uuid": accountId}, {"_id": 0})
    return _toAccountResponse(updated) if updated else None


async def getComponents(db: AsyncIOMotorDatabase, accountId: str) -> dict | None:
    """계정의 능력치/요구 능력치 ID 목록."""
    if not await db.teaming.find_one({"user_uuid": accountId}, {"_id": 0}):
        return None

    abilities = await db.abilities.find(
        {"$or": [{"user_uuid": accountId}, {"accountId": accountId}]},
        {"_id": 0, "abilityId": 1},
    ).to_list(length=10000)
    requirements = await db.requirements.find(
        {"$or": [{"user_uuid": accountId}, {"accountId": accountId}]},
        {"_id": 0, "requirementId": 1},
    ).to_list(length=10000)

    return {
        "accountId": accountId,
        "abilityIds": [a["abilityId"] for a in abilities],
        "requirementIds": [r["requirementId"] for r in requirements],
    }
