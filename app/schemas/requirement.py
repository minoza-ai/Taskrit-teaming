from pydantic import BaseModel

class RequirementResponse(BaseModel):
    """요구 능력치 응답."""
    
    requirementId: str
    accountId: str
    abilityText: str
    domain: str | None = None
    job: str | None = None
    proficiency: str | None = None
    techStack: list[str] | None = None
    legacyDegree: str | None = None

    model_config = {"from_attributes": True}
