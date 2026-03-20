"""계정 비즈니스 로직."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.ability import Ability
from app.models.requirement import Requirement
from app.services import gemini
from app.services import qdrant as qdrantService

async def createAccount(db: AsyncSession, accountId: str, accountType: str, abilityText: str, cost: int = 0) -> Account:
    """계정 생성 — 능력치 분해 + 임베딩 포함."""
    account = Account(
        accountId=accountId,
        type=accountType,
        abilityText=abilityText,
        cost=cost,
    )
    db.add(account)

    # 능력치 분해
    skills = await gemini.decomposeAbilities(abilityText)
    if skills:
        vectors = await gemini.embedTexts(skills)
        for skillText, vector in zip(skills, vectors):
            ability = Ability(
                abilityId=str(uuid.uuid4()),
                accountId=accountId,
                abilityText=skillText,
            )
            db.add(ability)
            qdrantService.upsertAbility(ability.abilityId, accountId, vector)

    # 에셋이면 요구 능력치도 생성
    if accountType == "asset":
        reqs = await gemini.decomposeRequirements(abilityText)
        if reqs:
            reqVectors = await gemini.embedTexts(reqs)
            for reqText, vector in zip(reqs, reqVectors):
                req = Requirement(
                    requirementId=str(uuid.uuid4()),
                    accountId=accountId,
                    abilityText=reqText,
                )
                db.add(req)
                qdrantService.upsertRequirement(req.requirementId, accountId, vector)

    await db.commit()
    await db.refresh(account)
    return account


async def deleteAccount(db: AsyncSession, accountId: str) -> bool:
    """계정 삭제."""
    account = await db.get(Account, accountId)
    if not account:
        return False

    qdrantService.deleteByAccount(accountId)
    await db.delete(account)
    await db.commit()
    return True


async def getAccount(db: AsyncSession, accountId: str) -> Account | None:
    """계정 조회."""
    return await db.get(Account, accountId)


async def updateAccount(db: AsyncSession, accountId: str, abilityText: str | None, availability: bool | None, cost: int | None) -> Account | None:
    """계정 상태 수정 — 능력치 변경 시 재분해."""
    account = await db.get(Account, accountId)
    if not account:
        return None

    if availability is not None:
        account.availability = availability
    if cost is not None:
        account.cost = cost

    if abilityText is not None and abilityText != account.abilityText:
        account.abilityText = abilityText

        # 기존 능력치 삭제
        oldAbilities = (await db.execute(select(Ability).where(Ability.accountId == accountId))).scalars().all()
        for a in oldAbilities:
            await db.delete(a)
        oldReqs = (await db.execute(select(Requirement).where(Requirement.accountId == accountId))).scalars().all()
        for r in oldReqs:
            await db.delete(r)
        qdrantService.deleteByAccount(accountId)

        # 재분해
        skills = await gemini.decomposeAbilities(abilityText)
        if skills:
            vectors = await gemini.embedTexts(skills)
            for skillText, vector in zip(skills, vectors):
                ability = Ability(abilityId=str(uuid.uuid4()), accountId=accountId, abilityText=skillText)
                db.add(ability)
                qdrantService.upsertAbility(ability.abilityId, accountId, vector)

        if account.type == "asset":
            reqs = await gemini.decomposeRequirements(abilityText)
            if reqs:
                reqVectors = await gemini.embedTexts(reqs)
                for reqText, vector in zip(reqs, reqVectors):
                    req = Requirement(requirementId=str(uuid.uuid4()), accountId=accountId, abilityText=reqText)
                    db.add(req)
                    qdrantService.upsertRequirement(req.requirementId, accountId, vector)

    await db.commit()
    await db.refresh(account)
    return account


async def getComponents(db: AsyncSession, accountId: str) -> dict | None:
    """계정의 능력치/요구 능력치 ID 목록."""
    account = await db.get(Account, accountId)
    if not account:
        return None

    abilities = (await db.execute(select(Ability.abilityId).where(Ability.accountId == accountId))).scalars().all()
    requirements = (await db.execute(select(Requirement.requirementId).where(Requirement.accountId == accountId))).scalars().all()

    return {
        "accountId": accountId,
        "abilityIds": list(abilities),
        "requirementIds": list(requirements),
    }
