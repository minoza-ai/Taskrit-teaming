"""능력치 / 요구 능력치 조회 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import getDb
from app.schemas.ability import AbilityResponse
from app.schemas.requirement import RequirementResponse

router = APIRouter(tags=["Ability"])

@router.get("/Ability/{abilityId}", response_model=AbilityResponse)
async def getAbility(abilityId: str, db: AsyncIOMotorDatabase = Depends(getDb)):
    """단일 능력치 조회."""
    ability = await db.abilities.find_one({"abilityId": abilityId}, {"_id": 0})
    if not ability:
        raise HTTPException(status_code=404, detail="Ability not found")
    return {
        "abilityId": ability.get("abilityId", abilityId),
        "accountId": ability.get("user_uuid", ""),
        "abilityText": ability.get("abilityText", ""),
    }

@router.get("/Requirement/{requirementId}", response_model=RequirementResponse)
async def getRequirement(requirementId: str, db: AsyncIOMotorDatabase = Depends(getDb)):
    """요구 능력치 조회."""
    requirement = await db.requirements.find_one({"requirementId": requirementId}, {"_id": 0})
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {
        "requirementId": requirement.get("requirementId", requirementId),
        "accountId": requirement.get("user_uuid", ""),
        "abilityText": requirement.get("abilityText", ""),
    }
