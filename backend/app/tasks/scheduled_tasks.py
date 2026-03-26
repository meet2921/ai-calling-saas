import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.db.sync_session import SessionLocal
from app.models.campaigns import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.services.campaign_service import start_campaign_sync

logger = logging.getLogger(__name__)


@celery_app.task
def trigger_scheduled_campaigns():
    """
    Runs every minute via Celery beat.
    Finds all campaigns with status=scheduled whose scheduled_at has passed
    and starts them automatically.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(Campaign)
            .filter(
                Campaign.status == CampaignStatus.scheduled,
                Campaign.scheduled_at <= now,
                Campaign.is_processing == False,
            )
            .all()
        )

        if not due:
            return

        for campaign in due:
            logger.info(
                "Auto-starting scheduled campaign %s (scheduled_at=%s)",
                campaign.id, campaign.scheduled_at,
            )
            try:
                start_campaign_sync(campaign, db)
            except Exception:
                logger.exception("Failed to auto-start campaign %s", campaign.id)

    finally:
        db.close()


@celery_app.task
def auto_complete_stale_campaigns():
    """
    Runs every minute via Celery beat.
    Finds campaigns stuck in 'running' with no active or pending leads
    and marks them as completed.
    """
    db = SessionLocal()
    try:
        running_campaigns = (
            db.query(Campaign)
            .filter(Campaign.status == CampaignStatus.running)
            .all()
        )

        for campaign in running_campaigns:
            active_count = (
                db.query(Lead)
                .filter(
                    Lead.campaign_id == campaign.id,
                    Lead.status.in_([
                        LeadStatus.PENDING,
                        LeadStatus.QUEUED,
                        LeadStatus.CALLING,
                    ]),
                )
                .count()
            )
            pending_retries = (
                db.query(Lead)
                .filter(
                    Lead.campaign_id == campaign.id,
                    Lead.status == LeadStatus.FAILED,
                    Lead.retry_count < Lead.max_retries,
                )
                .count()
            )

            if active_count == 0 and pending_retries == 0:
                campaign.status = CampaignStatus.completed
                campaign.is_processing = False
                campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                logger.info("Auto-completed stale campaign %s", campaign.id)

        db.commit()

    except Exception:
        logger.exception("auto_complete_stale_campaigns failed")
        db.rollback()
    finally:
        db.close()
