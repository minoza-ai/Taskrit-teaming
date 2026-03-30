"""계정 비즈니스 로직."""

import uuid
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import gemini
from app.services import qdrant as qdrantService

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
    """계정 생성 — 능력치 분해 + 임베딩 포함."""
    account = {
        "accountId": accountId,
        "userId": userId,
        "nickname": nickname,
        "type": accountType,
        "elo": 1000,
        "abilityText": abilityText,
        "availability": True,
        "cost": cost,
        "joinDate": datetime.utcnow(),
    }
    await db.accounts.insert_one(account)

    if not skipAi and abilityText.strip():
        # 능력치 분해
        skills = await gemini.decomposeAbilities(abilityText)
        if skills:
            vectors = await gemini.embedTexts(skills)
            for skillText, vector in zip(skills, vectors):
                abilityId = str(uuid.uuid4())
                await db.abilities.insert_one(
                    {
                        "abilityId": abilityId,
                        "accountId": accountId,
                        "abilityText": skillText,
                    }
                )
                qdrantService.upsertAbility(abilityId, accountId, vector)

    # 에셋이면 요구 능력치도 생성
    if accountType == "asset" and not skipAi and abilityText.strip():
        reqs = await gemini.decomposeRequirements(abilityText)
        if reqs:
            reqs = reqs[:1]  # 에셋 오퍼레이터는 현재 1명만 할당되므로 가장 첫 번째 요구 능력치 1개만 저장
            reqVectors = await gemini.embedTexts(reqs)
            for reqText, vector in zip(reqs, reqVectors):
                requirementId = str(uuid.uuid4())
                await db.requirements.insert_one(
                    {
                        "requirementId": requirementId,
                        "accountId": accountId,
                        "abilityText": reqText,
                    }
                )
                qdrantService.upsertRequirement(requirementId, accountId, vector)

    account.pop("_id", None)
    return account


async def deleteAccount(db: AsyncIOMotorDatabase, accountId: str) -> bool:
    """계정 삭제."""
    account = await db.accounts.find_one({"accountId": accountId}, {"_id": 0})
    if not account:
        return False

    qdrantService.deleteByAccount(accountId)
    await db.accounts.delete_one({"accountId": accountId})
    await db.abilities.delete_many({"accountId": accountId})
    await db.requirements.delete_many({"accountId": accountId})
    await db.tasks.delete_many({"accountId": accountId})
    return True


async def getAccount(db: AsyncIOMotorDatabase, accountId: str) -> dict | None:
    """계정 조회."""
    return await db.accounts.find_one({"accountId": accountId}, {"_id": 0})


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
    """계정 상태 수정 — 능력치 변경 시 재분해."""
    account = await db.accounts.find_one({"accountId": accountId}, {"_id": 0})
    if not account:
        return None

    setDoc: dict = {}
    if availability is not None:
        setDoc["availability"] = availability
    if cost is not None:
        setDoc["cost"] = cost
    if userId is not None:
        setDoc["userId"] = userId
    if nickname is not None:
        setDoc["nickname"] = nickname

    previousAbilityText = account.get("abilityText", "")

    if abilityText is not None and abilityText != previousAbilityText:
        setDoc["abilityText"] = abilityText

        # 기존 능력치 삭제
        await db.abilities.delete_many({"accountId": accountId})
        await db.requirements.delete_many({"accountId": accountId})
        qdrantService.deleteByAccount(accountId)

        if not skipAi and abilityText.strip():
            # 재분해
            skills = await gemini.decomposeAbilities(abilityText)
            if skills:
                vectors = await gemini.embedTexts(skills)
                for skillText, vector in zip(skills, vectors):
                    abilityId = str(uuid.uuid4())
                    await db.abilities.insert_one(
                        {
                            "abilityId": abilityId,
                            "accountId": accountId,
                            "abilityText": skillText,
                        }
                    )
                    qdrantService.upsertAbility(abilityId, accountId, vector)

        if account.get("type") == "asset" and not skipAi and abilityText.strip():
            reqs = await gemini.decomposeRequirements(abilityText)
            if reqs:
                reqs = reqs[:1]  # 업데이트 시에도 1개의 요구 능력치만 저장
                reqVectors = await gemini.embedTexts(reqs)
                for reqText, vector in zip(reqs, reqVectors):
                    requirementId = str(uuid.uuid4())
                    await db.requirements.insert_one(
                        {
                            "requirementId": requirementId,
                            "accountId": accountId,
                            "abilityText": reqText,
                        }
                    )
                    qdrantService.upsertRequirement(requirementId, accountId, vector)

    if setDoc:
        await db.accounts.update_one({"accountId": accountId}, {"$set": setDoc})

    return await db.accounts.find_one({"accountId": accountId}, {"_id": 0})


async def getComponents(db: AsyncIOMotorDatabase, accountId: str) -> dict | None:
    """계정의 능력치/요구 능력치 ID 목록."""
    account = await db.accounts.find_one({"accountId": accountId}, {"_id": 0})
    if not account:
        return None

    abilities = await db.abilities.find({"accountId": accountId}, {"_id": 0, "abilityId": 1}).to_list(length=10000)
    requirements = await db.requirements.find({"accountId": accountId}, {"_id": 0, "requirementId": 1}).to_list(length=10000)

    return {
        "accountId": accountId,
        "abilityIds": [a["abilityId"] for a in abilities],
        "requirementIds": [r["requirementId"] for r in requirements],
    }
