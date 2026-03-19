import time
from uuid import UUID
from app.core.celery_app import celery_app
from app.db.sync_session import SessionLocal
from app.models.campaigns import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.models.wallet import Wallet
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

            leads = db.query(Lead).filter(
                Lead.campaign_id == campaign.id,
                Lead.status.in_([LeadStatus.PENDING, LeadStatus.FAILED]),
                Lead.retry_count < Lead.max_retries,
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

                wallet = db.query(Wallet).filter(
                    Wallet.organization_id == campaign.organization_id
                ).first()

                if not wallet or wallet.minutes_balance <= 0:
                    print(
                        f"Campaign {campaign_id} stopped — "
                        f"insufficient balance"
                    )
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
                    print(f"Call failed for {lead.phone}: {str(e)}")

                    lead.attempts += 1
                    lead.retry_count += 1

                    if lead.retry_count >= lead.max_retries:
                        lead.status = LeadStatus.FAILED
                    else:
                        lead.status = LeadStatus.PENDING

                    db.commit()

                # Rate limiting between calls
                time.sleep(campaign.call_delay_seconds)

        print("Campaign execution stopped safely")

    except Exception as exc:
        print("Critical task error:", str(exc))
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