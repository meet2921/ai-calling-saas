from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json
import logging

from app.db.session import get_db
from app.models.call_logs import CallLog
from app.models.lead import Lead

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/bolna/webhook", status_code=status.HTTP_200_OK)
async def bolna_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Production-ready Bolna webhook handler
    - Handles empty payloads
    - Handles invalid JSON
    - Idempotent (prevents duplicates)
    - Transaction safe
    """

    # -------------------------
    # 1. Read raw body safely
    # -------------------------
    raw_body = await request.body()

    if not raw_body:
        logger.warning("Bolna webhook received empty body")
        return {"status": "ignored", "reason": "empty body"}

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("Bolna webhook invalid JSON", extra={"body": raw_body})
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("Bolna webhook received", extra={"payload": payload})

    # -------------------------
    # 2. Validate minimum data
    # -------------------------
    campaign_id = payload.get("campaign_id")
    lead_id = payload.get("lead_id")
    call_id = payload.get("call_id")  # IMPORTANT: unique call id from Bolna
    status_value = payload.get("status")

    if not campaign_id or not call_id:
        logger.warning("Missing campaign_id or call_id", extra={"payload": payload})
        return {"status": "ignored", "reason": "missing identifiers"}

    # -------------------------
    # 3. Idempotency check
    # -------------------------
    existing = await db.scalar(
        select(CallLog.id).where(CallLog.external_call_id == call_id)
    )

    if existing:
        logger.info("Duplicate webhook ignored", extra={"call_id": call_id})
        return {"status": "duplicate"}

    # -------------------------
    # 4. Normalize fields
    # -------------------------
    appointment_date = payload.get("appointment_date")
    if appointment_date:
        try:
            appointment_date = datetime.fromisoformat(appointment_date)
        except ValueError:
            appointment_date = None

    # -------------------------
    # 5. Create CallLog
    # -------------------------
    call_log = CallLog(
        external_call_id=call_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        user_number=payload.get("phone_number"),
        duration=payload.get("duration", 0),
        cost=payload.get("cost", 0),
        status=status_value,
        recording_url=payload.get("recording_url"),
        transcript=payload.get("transcript"),
        interest_level=payload.get("interest_level"),
        appointment_booked=payload.get("appointment_booked", False),
        appointment_date=appointment_date,
        appointment_mode=payload.get("appointment_mode"),
        customer_sentiment=payload.get("customer_sentiment"),
        final_call_summary=payload.get("final_summary"),
        summary=payload.get("summary"),
        transfer_call=payload.get("transfer_call", False),
        executed_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )

    # -------------------------
    # 6. Transaction-safe DB write
    # -------------------------
    try:
        db.add(call_log)

        if lead_id:
            lead = await db.get(Lead, lead_id)
            if lead:
                lead.status = status_value
                lead.last_contacted_at = datetime.utcnow()

        await db.commit()

    except Exception as e:
        await db.rollback()
        logger.exception("Failed to process Bolna webhook")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    # -------------------------
    # 7. Success
    # -------------------------
    return {
        "status": "processed",
        "call_id": call_id,
    }