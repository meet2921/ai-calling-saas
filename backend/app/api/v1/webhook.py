from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime           
import json
import logging

from app.db.session import get_db
from app.models.call_logs import CallLog
from app.models.lead import Lead, LeadStatus
from app.models.campaigns import Campaign
from app.services.wallet_service import deduct_minutes_for_call

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/bolna/webhook", status_code=status.HTTP_200_OK)
async def bolna_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
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

    root_payload = payload

    event_type = root_payload.get("event")

    if "data" in root_payload and isinstance(root_payload["data"], dict):
        payload = root_payload["data"]
    else:
        payload = root_payload

    if event_type and not event_type.startswith("call"):
        return {"status": "ignored", "reason": f"event {event_type} not processed"}

    # ── Extract Identifiers ───────────────────────────────
    call_id = payload.get("call_id") or payload.get("id")
    status_value = payload.get("status")

    if not call_id:
        logger.warning("Bolna webhook missing call_id", extra={"payload": payload})
        return {"status": "ignored", "reason": "missing call_id"}

    # ── Extract Phone Number ──────────────────────────────
    user_number = (
        payload.get("user_number")
        or payload.get("phone_number")
        or payload.get("recipient_phone_number")
        or payload.get("context_details", {}).get("recipient_phone_number")
        or payload.get("telephony_data", {}).get("to_number")
    )

    # ── Extract campaign_id and lead_id ───────────────────
    metadata = (
        payload.get("metadata")
        or root_payload.get("metadata")
        or {}
    )

    campaign_id = (
        payload.get("campaign_id")
        or metadata.get("campaign_id")
    )

    lead_id = (
        payload.get("lead_id")
        or metadata.get("lead_id")
    )

    # ── Fallback 1: lookup by external_call_id ────────────
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
                    extra={"call_id": call_id, "lead_id": lead_id}
                )
        except Exception as e:
            logger.warning(
                "Failed to lookup lead by external_call_id",
                extra={"error": str(e)}
            )

    # ── Fallback 2: lookup by phone number ────────────────
    if not campaign_id and not lead_id and user_number:
        clean_phone = user_number.lstrip("+").replace(" ", "").replace("-", "")

        if clean_phone.startswith("91") and len(clean_phone) > 10:
            local_phone = clean_phone[2:]
        else:
            local_phone = clean_phone

        phone_variants = [local_phone, clean_phone, user_number]

        for phone_variant in phone_variants:
            try:
                result = await db.execute(
                    select(Lead).where(Lead.phone == phone_variant)
                )
                lead_obj = result.scalar_one_or_none()
                if lead_obj:
                    campaign_id = str(lead_obj.campaign_id)
                    lead_id = str(lead_obj.id)
                    lead_obj.external_call_id = call_id
                    logger.info(
                        "Found lead via phone",
                        extra={"phone": phone_variant, "lead_id": lead_id}
                    )
                    break
            except Exception as e:
                logger.warning(
                    "Failed to lookup lead by phone",
                    extra={"error": str(e), "phone": phone_variant}
                )

    if not campaign_id:
        logger.warning(
            "campaign_id not found — storing null",
            extra={"user_number": user_number, "call_id": call_id}
        )

    # ── Normalize Fields ──────────────────────────────────
    duration = payload.get("conversation_duration")
    if duration is None:
        duration = payload.get("telephony_data", {}).get("duration", 0)

    try:
        duration = float(duration or 0)
    except (ValueError, TypeError):
        duration = 0.0

    cost = payload.get("total_cost", 0)
    try:
        cost = float(cost or 0)
    except (ValueError, TypeError):
        cost = 0.0

    appointment_date = payload.get("appointment_date")
    if appointment_date:
        try:
            appointment_date = datetime.fromisoformat(appointment_date)  # ✅ fixed
        except Exception:
            appointment_date = None

    # ── Idempotency Check ─────────────────────────────────
    result = await db.execute(
        select(CallLog).where(CallLog.external_call_id == call_id)
    )
    existing_log = result.scalar_one_or_none()

    # This will hold whichever log we use (existing or new)
    active_log = None

    try:

        # ── CASE 1: CallLog exists → UPDATE ──────────────
        if existing_log:
            existing_log.duration         = duration
            existing_log.cost             = cost
            existing_log.status           = status_value
            existing_log.recording_url    = payload.get("telephony_data", {}).get("recording_url")
            existing_log.transcript       = payload.get("transcript")
            existing_log.customer_sentiment = (
                payload.get("extracted_data", {}) or {}
            ).get("customer_sentiment")
            existing_log.interest_level   = (
                payload.get("extracted_data", {}) or {}
            ).get("interest_level")
            existing_log.final_call_summary = payload.get("summary")
            existing_log.summary          = payload.get("summary")
            existing_log.transfer_call    = payload.get("transfer_call", False)

            if campaign_id:
                existing_log.campaign_id = campaign_id
            if lead_id:
                existing_log.lead_id = lead_id

            active_log = existing_log 
        # ── CASE 2: CallLog missing → CREATE ─────────────
        else:
            if not lead_id:
                logger.warning(
                    "CallLog missing and lead not resolved. Ignoring.",
                    extra={"call_id": call_id}
                )
                return {"status": "ignored", "reason": "call_log_not_found"}

            logger.warning(
                "CallLog not found — creating from webhook.",
                extra={"call_id": call_id}
            )

            new_log = CallLog(
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
                executed_at=datetime.utcnow(),   # ✅ fixed
                created_at=datetime.utcnow(),    # ✅ fixed
            )
            db.add(new_log)
            await db.flush()  # get new_log.id immediately

            active_log = new_log  # ← track which log we used

        # ── Update Lead Status ────────────────────────────
        if lead_id:
            lead = await db.get(Lead, lead_id)
            if lead:
                bolna_to_lead_status = {
                    "initiated":         "calling",
                    "in-progress":       "calling",
                    "ringing":           "calling",
                    "completed":         "completed",
                    "call-disconnected": "completed",
                    "no-answer":         "failed",
                    "failed":            "failed",
                }
                lead_status = bolna_to_lead_status.get(status_value, "calling")
                lead.status = LeadStatus(lead_status)
                lead.external_call_id = call_id

                # Log call failures or rejections
                if status_value in ["failed", "no-answer", "call-disconnected"]:
                    logger.error(
                        f"Call System--> Call rejected by user--> Logged correctly",
                        extra={
                            "call_id": call_id,
                            "lead_id": lead_id,
                            "campaign_id": campaign_id,
                            "user_number": user_number,
                            "status": status_value
                        }
                    )

        # ── Deduct Minutes from Wallet ────────────────────
        # active_log covers both existing and newly created logs
        # double deduction check prevents charging twice
        if active_log and status_value in ("completed", "call-disconnected") and duration > 0:
            if campaign_id:
                from app.models.wallet import WalletTransaction

                # Check if already deducted for this call
                already_deducted = await db.scalar(
                    select(func.count())
                    .select_from(WalletTransaction)
                    .where(WalletTransaction.call_log_id == active_log.id)
                )

                if already_deducted == 0:
                    try:
                        campaign_result = await db.execute(
                            select(Campaign).where(Campaign.id == campaign_id)
                        )
                        campaign_obj = campaign_result.scalar_one_or_none()

                        if campaign_obj:
                            deduction = await deduct_minutes_for_call(
                                organization_id=str(campaign_obj.organization_id),
                                duration_seconds=duration,
                                call_log_id=str(active_log.id),
                                db=db
                            )
                            logger.warning(
                                f"Minutes deducted | "
                                f"Call: {call_id} | "
                                f"Duration: {duration}s | "
                                f"Deducted: {deduction['minutes_deducted']} min | "
                                f"Remaining: {deduction['new_balance']} min"
                            )
                        else:
                            logger.warning(
                                f"Campaign {campaign_id} not found "
                                f"— skipping deduction"
                            )

                    except Exception as e:
                        # Wallet error must NOT stop webhook
                        # Call data is saved even if deduction fails
                        logger.error(
                            f"Wallet deduction failed for call {call_id}: {e}"
                        )
                else:
                    logger.info(
                        f"Skipping deduction — already charged for call {call_id}"
                    )

        await db.commit()

    except Exception:
        await db.rollback()
        logger.exception("Failed to process Bolna webhook update")
        raise HTTPException(status_code=500, detail="Webhook processing failed")