import time
from uuid import UUID

from app.core.celery_app import celery_app
from app.db.sync_session import SessionLocal
from app.models.campaigns import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.services.bolna_service import make_call


@celery_app.task(bind=True, max_retries=3)
def process_campaign(self, campaign_id: str):

    db = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == UUID(campaign_id)
        ).first()

        if not campaign:
            print("Campaign not found")
            return

        print(f"Processing campaign {campaign.id}")

        while True:

            db.refresh(campaign)

            # STOP / PAUSE CHECK
            if campaign.status != CampaignStatus.running:
                print("Campaign paused or stopped")
                break

            # ✅ FIXED QUERY (retry safe)
            leads = db.query(Lead).filter(
                Lead.campaign_id == campaign.id,
                Lead.status.in_([LeadStatus.PENDING, LeadStatus.FAILED]),
                Lead.retry_count < Lead.max_retries
            ).limit(5).all()

            if not leads:
                campaign.status = CampaignStatus.completed
                campaign.is_processing = False
                db.commit()
                print("Campaign completed")
                break

            for lead in leads:

                db.refresh(campaign)

                if campaign.status != CampaignStatus.running:
                    print("Campaign paused during execution")
                    break

                try:
                    # Mark as queued
                    lead.status = LeadStatus.QUEUED
                    db.commit()

                    formatted_phone = f"+91{lead.phone}"

                    # Make call
                    response = make_call(
                        phone=formatted_phone,
                        agent_id=campaign.bolna_agent_id
                    )

                    # SUCCESS
                    lead.external_call_id = response.get("call_id")
                    lead.status = LeadStatus.COMPLETED
                    lead.attempts += 1
                    lead.retry_count = 0  # reset on success
                    db.commit()

                except Exception as e:
                    print(f"Call failed for {lead.phone}: {str(e)}")

                    lead.attempts += 1
                    lead.retry_count += 1

                    if lead.retry_count >= lead.max_retries:
                        lead.status = LeadStatus.FAILED
                    else:
                        lead.status = LeadStatus.PENDING

                    db.commit()

                # Rate limit
                time.sleep(campaign.call_delay_seconds)

        print("Campaign execution stopped safely")

    except Exception as exc:
        print("Critical task error:", str(exc))
        self.retry(exc=exc, countdown=5)

    finally:
        campaign = db.query(Campaign).filter(
            Campaign.id == UUID(campaign_id)
        ).first()

        if campaign:
            campaign.is_processing = False
            db.commit()

        db.close()