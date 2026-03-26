import logging
import time
from uuid import UUID
from app.core.celery_app import celery_app
from app.db.sync_session import SessionLocal
from app.models.campaigns import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.models.wallet import Wallet
from app.services.bolna_service import make_call

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_campaign(self, campaign_id: str):

    db = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == UUID(campaign_id)
        ).first()

        if not campaign:
            logger.warning("Campaign %s not found", campaign_id)
            return

        logger.info("Processing campaign %s", campaign.id)

        while True:

            db.refresh(campaign)

            # STOP / PAUSE CHECK
            if campaign.status != CampaignStatus.running:
                logger.info("Campaign %s is %s — stopping", campaign_id, campaign.status.value)
                break

            leads = db.query(Lead).filter(
                Lead.campaign_id == campaign.id,
                Lead.status.in_([LeadStatus.PENDING, LeadStatus.FAILED]),
                Lead.retry_count < Lead.max_retries,
            ).limit(5).all()

            if not leads:
                # Check if any calls are still in-flight (CALLING or QUEUED)
                active_count = db.query(Lead).filter(
                    Lead.campaign_id == campaign.id,
                    Lead.status.in_([LeadStatus.CALLING, LeadStatus.QUEUED]),
                ).count()

                if active_count > 0:
                    logger.info(
                        "Campaign %s waiting for %d active call(s) to complete",
                        campaign_id, active_count,
                    )
                    time.sleep(15)
                    continue

                campaign.status = CampaignStatus.completed
                campaign.is_processing = False
                db.commit()
                logger.info("Campaign %s completed", campaign_id)
                break

            for lead in leads:

                db.refresh(campaign)

                if campaign.status != CampaignStatus.running:
                    logger.info("Campaign %s paused during execution", campaign_id)
                    break

                wallet = db.query(Wallet).filter(
                    Wallet.organization_id == campaign.organization_id
                ).first()

                if not wallet or wallet.minutes_balance <= 0:
                    logger.warning("Campaign %s paused — insufficient balance", campaign_id)
                    campaign.status = CampaignStatus.paused
                    campaign.is_processing = False
                    db.commit()
                    return

                try:
                    # Mark as queued before attempting the call
                    lead.status = LeadStatus.QUEUED
                    db.commit()

                    formatted_phone = f"+91{lead.phone}"

                    # make_call() handles its own flush+commit internally
                    # so the CallLog exists before the webhook fires
                    response = make_call(
                        db=db,
                        phone=formatted_phone,
                        agent_id=campaign.bolna_agent_id,
                        campaign_id=campaign.id,
                        lead_id=lead.id,
                    )

                    # Call was accepted by Bolna — mark as CALLING, not COMPLETED.
                    # The webhook will update status to completed/failed
                    # when the call actually finishes.
                    lead.status = LeadStatus.CALLING
                    lead.attempts += 1
                    lead.retry_count = 0
                    db.commit()

                except Exception as e:
                    logger.error("Call failed for %s: %s", lead.phone, e)

                    lead.attempts += 1
                    lead.retry_count += 1

                    if lead.retry_count >= lead.max_retries:
                        lead.status = LeadStatus.FAILED
                    else:
                        lead.status = LeadStatus.PENDING

                    db.commit()

                # Rate limiting between calls
                time.sleep(campaign.call_delay_seconds)

        logger.info("Campaign %s execution stopped safely", campaign_id)

    except Exception as exc:
        logger.exception("Critical task error in campaign %s", campaign_id)
        self.retry(exc=exc, countdown=5)

    finally:
        # Always release is_processing lock, even on crash
        try:
            campaign = db.query(Campaign).filter(
                Campaign.id == UUID(campaign_id)
            ).first()

            if campaign:
                campaign.is_processing = False
                db.commit()
        except Exception:
            pass  # don't mask the original exception

        db.close()