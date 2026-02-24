from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    bolna_agent_id: str | None = None

class CampaignResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    bolna_agent_id: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True