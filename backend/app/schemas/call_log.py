from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class CallLogResponse(BaseModel):
    id: UUID
    campaign_id: UUID | None
    lead_id: UUID | None
    external_call_id: str
    user_number: str | None
    status: str | None
    duration: int
    cost: float
    recording_url: str | None
    transcript: str | None
    summary: str | None
    final_call_summary: str | None
    interest_level: str | None
    appointment_booked: bool
    appointment_date: datetime | None
    appointment_mode: str | None
    customer_sentiment: str | None
    transfer_call: bool
    scheduled_at: datetime | None
    executed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
