from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any
from app.models.lead import LeadStatus


class LeadResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    organization_id: UUID
    phone: str
    status: LeadStatus
    attempts: int
    retry_count: int
    max_retries: int
    custom_fields: dict[str, Any]
    external_call_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadStatusUpdate(BaseModel):
    status: LeadStatus
