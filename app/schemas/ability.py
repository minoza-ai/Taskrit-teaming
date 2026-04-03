from pydantic import BaseModel

class AbilityResponse(BaseModel):
    """단일 능력치 응답."""
    
    abilityId: str
    accountId: str
    abilityText: str
    domain: str | None = None
    job: str | None = None
    proficiency: str | None = None
    techStack: list[str] | None = None
    legacyDegree: str | None = None

    model_config = {"from_attributes": True}
