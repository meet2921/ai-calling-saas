from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
