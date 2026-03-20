from pydantic import BaseModel


class AbilityResponse(BaseModel):
    """단일 능력치 응답."""
    abilityId: str
    accountId: str
    abilityText: str

    model_config = {"from_attributes": True}
