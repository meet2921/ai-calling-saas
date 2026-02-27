from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json
import logging

from app.db.session import get_db
from app.models.call_logs import CallLog
from app.models.lead import Lead, LeadStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/bolna/webhook", status_code=status.HTTP_200_OK)
async def bolna_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    print("HEADERS:", dict(request.headers))
    print("RAW BODY:", raw_body.decode(errors="ignore"))

    if not raw_body:
        logger.warning("Bolna webhook received empty body")
        return {"status": "ignored", "reason": "empty body"}

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("Bolna webhook invalid JSON", extra={"body": raw_body})
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("Bolna webhook received", extra={"payload": payload})

    # Handle wrapper
    event_type = payload.get("event")
    if "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]

    if event_type and event_type != "call.completed":
        return {"status": "ignored", "reason": f"event {event_type} not processed"}

    # -------------------------
    # 3. Extract Identifiers (call_id first, it's mandatory for idempotency)
    # -------------------------
    call_id = payload.get("call_id") or payload.get("id")
    status_value = payload.get("status")

    if not call_id:
        logger.warning("Bolna webhook missing call_id", extra={"payload": payload})
        return {"status": "ignored", "reason": "missing call_id"}

    # -------------------------
    # Extract phone number early for lead lookup
    # -------------------------
    user_number = (
        payload.get("user_number")
        or payload.get("phone_number")
        or payload.get("recipient_phone_number")
        or payload.get("context_details", {}).get("recipient_phone_number")
        or payload.get("telephony_data", {}).get("to_number")
    )

    # Try to get campaign_id and lead_id from payload or metadata first
    campaign_id = payload.get("campaign_id") or payload.get("metadata", {}).get("campaign_id")
    lead_id = payload.get("lead_id") or payload.get("metadata", {}).get("lead_id")

    # Fallback 1: look up by external_call_id (set when call was initiated)
    if not campaign_id and not lead_id:
        try:
            result = await db.execute(
                select(Lead).where(Lead.external_call_id == call_id)
            )
            lead_obj = result.scalar_one_or_none()
            if lead_obj:
                campaign_id = str(lead_obj.campaign_id)
                lead_id = str(lead_obj.id)
                logger.info(
                    "Found lead via external_call_id",
                    extra={"call_id": call_id, "lead_id": lead_id, "campaign_id": campaign_id}
                )
        except Exception as e:
            logger.warning("Failed to lookup lead by external_call_id", extra={"error": str(e)})

    # Fallback 2: look up by phone number (matches campaign leads)
    if not campaign_id and not lead_id and user_number:
        # Phone numbers in leads table are stored without country code (e.g., "7284885875")
        # but webhook sends full international format (e.g., "+917284885875")
        # Extract just the local number part
        clean_phone = user_number.lstrip("+").replace(" ", "").replace("-", "")
        
        # For India (+91), remove country code to get local number
        if clean_phone.startswith("91") and len(clean_phone) > 10:
            local_phone = clean_phone[2:]  # Remove "91"
        else:
            local_phone = clean_phone
        
        phone_variants = [local_phone, clean_phone, user_number]  # Try all variants
        
        logger.info(
            "Looking up lead by phone",
            extra={
                "user_number": user_number,
                "local_phone": local_phone,
                "variants": phone_variants
            }
        )
        
        for phone_variant in phone_variants:
            try:
                result = await db.execute(
                    select(Lead).where(Lead.phone == phone_variant)
                )
                lead_obj = result.scalar_one_or_none()
                if lead_obj:
                    campaign_id = str(lead_obj.campaign_id)
                    lead_id = str(lead_obj.id)
                    # Update lead's external_call_id for future reference
                    lead_obj.external_call_id = call_id
                    logger.info(
                        "Found lead via phone number",
                        extra={
                            "phone_variant": phone_variant,
                            "lead_id": lead_id,
                            "campaign_id": campaign_id,
                        }
                    )
                    break  # Found it, stop searching
            except Exception as e:
                logger.warning(
                    "Failed to lookup lead by phone variant",
                    extra={"error": str(e), "phone": phone_variant}
                )

    if not campaign_id:
        logger.warning(
            "Bolna webhook campaign_id not provided and lead not found; storing null",
            extra={"user_number": user_number, "call_id": call_id}
        )

    # -------------------------
    # Normalize fields
    # -------------------------

    # Duration
    duration = payload.get("conversation_duration")
    if duration is None:
        duration = payload.get("telephony_data", {}).get("duration", 0)

    try:
        duration = float(duration or 0)
    except (ValueError, TypeError):
        duration = 0.0

    # Cost
    cost = payload.get("total_cost", 0)
    try:
        cost = float(cost or 0)
    except (ValueError, TypeError):
        cost = 0.0

    appointment_date = payload.get("appointment_date")
    if appointment_date:
        try:
            appointment_date = datetime.fromisoformat(appointment_date)
        except Exception:
            appointment_date = None

    # -------------------------
    # Idempotency Check
    # -------------------------
    result = await db.execute(
        select(CallLog).where(CallLog.external_call_id == call_id)
    )
    existing_log = result.scalar_one_or_none()

    try:
        if existing_log:
            # UPDATE
            existing_log.duration = duration
            existing_log.cost = cost
            existing_log.status = status_value
            existing_log.recording_url = payload.get("telephony_data", {}).get("recording_url")
            existing_log.transcript = payload.get("transcript")
            existing_log.customer_sentiment = (
                payload.get("extracted_data", {}) or {}
            ).get("customer_sentiment")
            existing_log.interest_level = (
                payload.get("extracted_data", {}) or {}
            ).get("interest_level")
            existing_log.final_call_summary = payload.get("summary")
            # Set campaign_id and lead_id if they were found via lookup
            if campaign_id:
                existing_log.campaign_id = campaign_id
            if lead_id:
                existing_log.lead_id = lead_id

        else:
            # CREATE
            call_log = CallLog(
                external_call_id=call_id,
                campaign_id=campaign_id,
                lead_id=lead_id,
                user_number=user_number,
                duration=duration,
                cost=cost,
                status=status_value,
                recording_url=payload.get("telephony_data", {}).get("recording_url"),
                transcript=payload.get("transcript"),
                interest_level=(
                    payload.get("extracted_data", {}) or {}
                ).get("interest_level"),
                appointment_booked=payload.get("appointment_booked", False),
                appointment_date=appointment_date,
                appointment_mode=payload.get("appointment_mode"),
                customer_sentiment=(
                    payload.get("extracted_data", {}) or {}
                ).get("customer_sentiment"),
                final_call_summary=payload.get("summary"),
                summary=payload.get("summary"),
                transfer_call=payload.get("transfer_call", False),
                executed_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )

            db.add(call_log)

        # Update Lead if exists
        if lead_id:
            lead = await db.get(Lead, lead_id)
            if lead:
                # Map Bolna call status to LeadStatus enum
                # Bolna statuses: initiated, in-progress, ringing, completed, no-answer, failed, call-disconnected
                bolna_to_lead_status = {
                    "initiated": "calling",
                    "in-progress": "calling",
                    "ringing": "calling",
                    "completed": "completed",
                    "call-disconnected": "completed",
                    "no-answer": "failed",
                    "failed": "failed",
                }
                lead_status = bolna_to_lead_status.get(status_value, "calling")
                lead.status = LeadStatus(lead_status)
                lead.external_call_id = call_id

        await db.commit()

    except Exception:
        await db.rollback()
        logger.exception("Failed to process Bolna webhook")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "processed", "call_id": call_id}