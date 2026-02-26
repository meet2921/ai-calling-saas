from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.session import get_db
from app.models.call_logs import CallLog
from app.models.lead import Lead

router = APIRouter()


@router.post("/bolna/webhook")
async def bolna_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()

    """
    Expected payload from Bolna:
    {
        "campaign_id": "...",
        "lead_id": "...",
        "phone_number": "...",
        "duration": 120,
        "cost": 0.45,
        "status": "completed",
        "recording_url": "...",
        "transcript": "...",
        "interest_level": "high",
        "appointment_booked": true,
        "appointment_date": "...",
        "appointment_mode": "offline",
        "customer_sentiment": "positive",
        "final_summary": "...",
        "summary": "...",
        "transfer_call": false
    }
    """

    call_log = CallLog(
        campaign_id=payload.get("campaign_id"),
        lead_id=payload.get("lead_id"),
        user_number=payload.get("phone_number"),
        duration=payload.get("duration", 0),
        cost=payload.get("cost", 0),
        status=payload.get("status"),
        recording_url=payload.get("recording_url"),
        transcript=payload.get("transcript"),
        interest_level=payload.get("interest_level"),
        appointment_booked=payload.get("appointment_booked", False),
        appointment_date=payload.get("appointment_date"),
        appointment_mode=payload.get("appointment_mode"),
        customer_sentiment=payload.get("customer_sentiment"),
        final_call_summary=payload.get("final_summary"),
        summary=payload.get("summary"),
        transfer_call=payload.get("transfer_call", False),
        executed_at=datetime.utcnow(),
    )

    db.add(call_log)

    # Optional: update lead status
    if payload.get("lead_id"):
        lead = await db.get(Lead, payload.get("lead_id"))
        if lead:
            lead.status = payload.get("status")

    await db.commit()

    return {"message": "Webhook processed successfully"}