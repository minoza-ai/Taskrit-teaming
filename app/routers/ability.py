"""능력치 / 요구 능력치 조회 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import getDb
from app.models.ability import Ability
from app.models.requirement import Requirement
from app.schemas.ability import AbilityResponse
from app.schemas.requirement import RequirementResponse

router = APIRouter(tags=["Ability"])


@router.get("/Ability/{abilityId}", response_model=AbilityResponse)
async def getAbility(abilityId: str, db: AsyncSession = Depends(getDb)):
    """단일 능력치 조회."""
    ability = await db.get(Ability, abilityId)
    if not ability:
        raise HTTPException(status_code=404, detail="Ability not found")
    return ability


@router.get("/Requirement/{requirementId}", response_model=RequirementResponse)
async def getRequirement(requirementId: str, db: AsyncSession = Depends(getDb)):
    """요구 능력치 조회."""
    requirement = await db.get(Requirement, requirementId)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement
