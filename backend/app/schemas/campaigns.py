
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum


# ✅ 1️⃣ Campaign Status Enum
class CampaignStatus(str, Enum):
    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    paused = "paused"
    completed = "completed"
    stopped = "stopped"


# ✅ 2️⃣ Create Schema
class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    bolna_agent_id: str | None = None


# ✅ 3️⃣ Status Update Schema (NEW for Step 2)
class CampaignStatusUpdate(BaseModel):
    status: CampaignStatus


# ✅ 4️⃣ Response Schema (UPDATED)
class CampaignResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    bolna_agent_id: str | None

    # 🔥 replaced is_active
    status: CampaignStatus

    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
