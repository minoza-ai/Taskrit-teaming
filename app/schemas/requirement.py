from pydantic import BaseModel

class RequirementResponse(BaseModel):
    """요구 능력치 응답."""
    
    requirementId: str
    accountId: str
    abilityText: str

    model_config = {"from_attributes": True}
