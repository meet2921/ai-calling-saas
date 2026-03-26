from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from uuid import UUID

from app.models.campaigns import Campaign, CampaignStatus
from app.tasks.campaign_tasks import process_campaign


async def get_campaign_or_404(db: AsyncSession, campaign_id: UUID):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


# 🚀 START CAMPAIGN
async def start_campaign(db: AsyncSession, campaign_id: UUID):
    campaign = await get_campaign_or_404(db, campaign_id)

    if campaign.status not in [CampaignStatus.draft, CampaignStatus.scheduled, CampaignStatus.paused, CampaignStatus.completed]:
        raise HTTPException(400, "Cannot start campaign from this state")

    if campaign.is_processing:
        raise HTTPException(400, "Campaign already processing")

    campaign.status = CampaignStatus.running
    campaign.is_processing = True
    campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(campaign)

    process_campaign.apply_async(
        args=[str(campaign.id)],
        queue="campaign_queue"
    )

    return campaign 


# ⏸ PAUSE CAMPAIGN
async def pause_campaign(db: AsyncSession, campaign_id: UUID):
    campaign = await get_campaign_or_404(db, campaign_id)

    if campaign.status != CampaignStatus.running:
        raise HTTPException(
            status_code=400,
            detail="Only running campaign can be paused",
        )

    campaign.status = CampaignStatus.paused
    campaign.is_processing = False
    campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(campaign)

    return campaign


# ▶ RESUME CAMPAIGN
async def resume_campaign(db: AsyncSession, campaign_id: UUID):
    campaign = await get_campaign_or_404(db, campaign_id)

    if campaign.status != CampaignStatus.paused:
        raise HTTPException(
            status_code=400,
            detail="Only paused campaign can be resumed",
        )

    campaign.status = CampaignStatus.running
    campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(campaign)

    process_campaign.delay(str(campaign.id))

    return campaign


# 🕐 START CAMPAIGN (sync — used by Celery beat scheduled task)
def start_campaign_sync(campaign: Campaign, db: Session) -> None:
    """Start a scheduled campaign from a sync Celery context."""
    if campaign.is_processing:
        return
    campaign.status = CampaignStatus.running
    campaign.is_processing = True
    campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    process_campaign.apply_async(args=[str(campaign.id)], queue="campaign_queue")


# 🛑 STOP CAMPAIGN
async def stop_campaign(db: AsyncSession, campaign_id: UUID):
    campaign = await get_campaign_or_404(db, campaign_id)

    if campaign.status in [CampaignStatus.completed, CampaignStatus.stopped]:
        raise HTTPException(
            status_code=400,
            detail="Campaign already stopped or completed",
        )

    campaign.status = CampaignStatus.stopped
    campaign.is_processing = False
    campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(campaign)

    return campaign