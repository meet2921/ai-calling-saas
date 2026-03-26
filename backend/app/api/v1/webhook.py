import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.db.session import get_db
from app.models.call_logs import CallLog
from app.models.lead import Lead, LeadStatus
from app.models.campaigns import Campaign, CampaignStatus
from app.models.wallet import WalletTransaction
from app.services.wallet_service import deduct_minutes_for_call

router = APIRouter()
logger = logging.getLogger(__name__)


# -------------------------
# Token Verification
# -------------------------

def _verify_webhook_token(token: str | None) -> None:
    """
    Verifies the secret token passed as ?token= in the webhook URL.

    In Bolna dashboard, register your webhook URL as:
        https://yourdomain.com/api/v1/bolna/webhook?token=YOUR_SECRET

    Generate a strong secret with:
        python -c "import secrets; print(secrets.token_hex(32))"

    If BOLNA_WEBHOOK_SECRET is not set in .env, verification is skipped
    (safe for local development only — always set it in production).
    """
    secret = settings.BOLNA_WEBHOOK_SECRET

    # Skip verification if secret is not configured
    if not secret:
        logger.warning(
            "BOLNA_WEBHOOK_SECRET is not set — skipping token verification. "
            "Set it in production."
        )
        return

    if not token:
        logger.warning("Webhook request missing ?token= query parameter")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook token",
        )

    # compare_digest prevents timing attacks
    if not hmac.compare_digest(secret, token.strip()):
        logger.warning("Webhook token mismatch — unauthorized request blocked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token",
        )

    logger.debug("Webhook token verified successfully")


# -------------------------
# Webhook Endpoint
# -------------------------

@router.post("/bolna/webhook", status_code=status.HTTP_200_OK)
async def bolna_webhook(
    request: Request,
    token: str | None = Query(default=None),  # reads ?token= from URL
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()

    if not raw_body:
        logger.warning("Bolna webhook received empty body")
        return {"status": "ignored", "reason": "empty body"}

    # Verify token FIRST — before touching any data
    _verify_webhook_token(token)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info("Bolna webhook received", extra={"payload": payload})

    root_payload = payload
    event_type = root_payload.get("event")

    if "data" in root_payload and isinstance(root_payload["data"], dict):
        payload = root_payload["data"]

    if event_type and not event_type.startswith("call"):
        return {"status": "ignored", "reason": f"event {event_type} not processed"}

    # -------------------------
    # Extract Call ID
    # -------------------------

    call_id = payload.get("call_id") or payload.get("id")
    status_value = payload.get("status")

    if not call_id:
        logger.warning("Missing call_id")
        return {"status": "ignored", "reason": "missing_call_id"}

    # -------------------------
    # Extract Phone
    # -------------------------

    user_number = (
        payload.get("user_number")
        or payload.get("phone_number")
        or payload.get("recipient_phone_number")
        or payload.get("context_details", {}).get("recipient_phone_number")
        or payload.get("telephony_data", {}).get("to_number")
    )

    metadata = payload.get("metadata") or root_payload.get("metadata") or {}

    lead_id = metadata.get("lead_id")
    campaign_id = metadata.get("campaign_id")

    lead_obj = None

    # -------------------------
    # Lead Lookup Strategy
    # -------------------------

    if lead_id:
        lead_obj = await db.get(Lead, lead_id)

    if not lead_obj:
        result = await db.execute(
            select(Lead).where(Lead.external_call_id == call_id)
        )
        lead_obj = result.scalar_one_or_none()

    if not lead_obj and user_number:

        clean_phone = user_number.lstrip("+").replace(" ", "").replace("-", "")

        if clean_phone.startswith("91") and len(clean_phone) > 10:
            local_phone = clean_phone[2:]
        else:
            local_phone = clean_phone

        phone_variants = [local_phone, clean_phone, user_number]

        for phone_variant in phone_variants:

            result = await db.execute(
                select(Lead).where(Lead.phone == phone_variant)
            )

            lead_obj = result.scalars().first()

            if lead_obj:
                logger.info(
                    "Lead resolved via phone",
                    extra={
                        "phone_variant": phone_variant,
                        "lead_id": lead_obj.id,
                    },
                )
                break

    if lead_obj and not lead_id:
        lead_id = str(lead_obj.id)

    if lead_obj and not campaign_id:
        campaign_id = str(lead_obj.campaign_id)

    # -------------------------
    # Duration
    # -------------------------

    duration = payload.get("conversation_duration")

    if duration is None:
        duration = payload.get("telephony_data", {}).get("duration", 0)

    try:
        duration = float(duration or 0)
    except Exception:
        duration = 0.0

    # -------------------------
    # Cost
    # -------------------------

    cost = payload.get("total_cost", 0)

    try:
        cost = float(cost or 0)
    except Exception:
        cost = 0.0

    # -------------------------
    # Appointment
    # -------------------------

    appointment_date = payload.get("appointment_date")

    if appointment_date:
        try:
            appointment_date = datetime.fromisoformat(appointment_date)
        except Exception:
            appointment_date = None

    # -------------------------
    # Find CallLog FIRST
    # -------------------------

    result = await db.execute(
        select(CallLog).where(CallLog.external_call_id == call_id)
    )
    existing_log = result.scalar_one_or_none()

    # Points to whichever log is used for deduction.
    # Assigned in both update and create paths below.
    log_for_deduction: CallLog | None = None

    try:

        # If CallLog exists → trust it as source of truth
        if existing_log:
            campaign_id = str(existing_log.campaign_id)
            lead_id = str(existing_log.lead_id)

        # -------------------------
        # Update existing CallLog
        # -------------------------

        if existing_log:

            existing_log.duration = duration
            existing_log.cost = cost
            existing_log.status = status_value
            existing_log.recording_url = payload.get("telephony_data", {}).get("recording_url")
            existing_log.transcript = payload.get("transcript")
            existing_log.summary = payload.get("summary")
            existing_log.final_call_summary = payload.get("summary")
            existing_log.transfer_call = payload.get("transfer_call", False)

            extracted = payload.get("extracted_data", {}) or {}
            existing_log.customer_sentiment = extracted.get("customer_sentiment")
            existing_log.interest_level = extracted.get("interest_level")

            log_for_deduction = existing_log

        # -------------------------
        # Create CallLog if missing
        # -------------------------

        else:

            if not lead_obj or not campaign_id:
                logger.warning(
                    "Skipping CallLog creation — lead or campaign could not be resolved "
                    "(call_id=%s lead_resolved=%s campaign_id=%s)",
                    call_id, lead_obj is not None, campaign_id,
                )
                return {"status": "ignored", "reason": "lead_or_campaign_unresolved"}

            logger.warning("Creating CallLog from webhook")

            new_log = CallLog(
                external_call_id=call_id,
                campaign_id=campaign_id,
                lead_id=str(lead_obj.id),
                user_number=user_number,
                duration=duration,
                cost=cost,
                status=status_value,
                recording_url=payload.get("telephony_data", {}).get("recording_url"),
                transcript=payload.get("transcript"),
                interest_level=(payload.get("extracted_data", {}) or {}).get("interest_level"),
                appointment_booked=payload.get("appointment_booked", False),
                appointment_date=appointment_date,
                appointment_mode=payload.get("appointment_mode"),
                customer_sentiment=(payload.get("extracted_data", {}) or {}).get("customer_sentiment"),
                final_call_summary=payload.get("summary"),
                summary=payload.get("summary"),
                transfer_call=payload.get("transfer_call", False),
                executed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

            db.add(new_log)

            # Flush so new_log.id is populated before deduction query
            await db.flush()

            log_for_deduction = new_log

        # -------------------------
        # Update Lead Status
        # -------------------------

        if lead_id:

            lead = await db.get(Lead, lead_id)

            if lead:

                status_map = {
                    "initiated": "calling",
                    "in-progress": "calling",
                    "ringing": "calling",
                    "completed": "completed",
                    "call-disconnected": "completed",
                    "no-answer": "no_answer",
                    "busy": "failed",
                    "failed": "failed",
                    "error": "failed",
                }

                lead_status = status_map.get(status_value, "failed")
                lead.status = LeadStatus(lead_status)
                lead.external_call_id = call_id
                lead.last_called = datetime.now(timezone.utc).replace(tzinfo=None)
                if duration > 0:
                    lead.duration = int(duration)

                # Check if all leads in the campaign are done and mark completed
                final_statuses = {LeadStatus.COMPLETED, LeadStatus.NO_ANSWER}
                is_terminal = LeadStatus(lead_status) in final_statuses or (
                    LeadStatus(lead_status) == LeadStatus.FAILED
                    and lead.retry_count >= lead.max_retries
                )
                if is_terminal and lead.campaign_id:
                    await db.flush()  # make this lead's new status visible to the count queries
                    active_count = await db.scalar(
                        select(func.count())
                        .select_from(Lead)
                        .where(
                            Lead.campaign_id == lead.campaign_id,
                            Lead.status.in_([
                                LeadStatus.PENDING,
                                LeadStatus.QUEUED,
                                LeadStatus.CALLING,
                            ]),
                        )
                    )
                    pending_retries = await db.scalar(
                        select(func.count())
                        .select_from(Lead)
                        .where(
                            Lead.campaign_id == lead.campaign_id,
                            Lead.status == LeadStatus.FAILED,
                            Lead.retry_count < Lead.max_retries,
                        )
                    )
                    if active_count == 0 and pending_retries == 0:
                        campaign_result = await db.execute(
                            select(Campaign).where(Campaign.id == lead.campaign_id)
                        )
                        camp = campaign_result.scalar_one_or_none()
                        if camp and camp.status == CampaignStatus.running:
                            camp.status = CampaignStatus.completed
                            camp.is_processing = False
                            camp.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                            logger.info("Campaign %s auto-completed via webhook", camp.id)

        # -------------------------
        # Wallet Deduction
        # Fires for BOTH existing and newly created CallLogs.
        # Only deducts once per call — guarded by WalletTransaction check.
        # Only deducts when call has duration (i.e. call actually connected).
        # -------------------------

        if duration > 0 and campaign_id and log_for_deduction:

            already_deducted = await db.scalar(
                select(func.count())
                .select_from(WalletTransaction)
                .where(WalletTransaction.call_log_id == log_for_deduction.id)
            )

            if already_deducted == 0:

                campaign_result = await db.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                )
                campaign_obj = campaign_result.scalar_one_or_none()

                if campaign_obj:

                    deduction = await deduct_minutes_for_call(
                        organization_id=str(campaign_obj.organization_id),
                        duration_seconds=duration,
                        call_log_id=str(log_for_deduction.id),
                        db=db,
                    )

                    logger.info(
                        f"Minutes deducted | Call {call_id} | "
                        f"Duration {duration}s | "
                        f"Deducted {deduction['minutes_deducted']} min"
                    )

        await db.commit()

    except Exception:

        await db.rollback()
        logger.exception("Webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "success"}