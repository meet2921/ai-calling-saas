from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from app.services.wallet_service import has_sufficient_balance, get_balance
from app.db.session import get_db
from app.models.campaigns import Campaign
from app.schemas.campaigns import CampaignCreate, CampaignResponse, CampaignStatusUpdate
from app.services.campaign_service import (
    start_campaign,
    pause_campaign,
    resume_campaign,
    stop_campaign
)
from app.core.deps import get_current_user
from app.services.bolna_service import get_agent_details
from app.models.user import User
from app.models.call_logs import CallLog

async def get_authorized_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 🔐 Organization-level authorization
    if campaign.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return campaign

router = APIRouter(tags=["Campaigns"])

@router.post("/", response_model=CampaignResponse)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
     # 🔹 Check if agent ID is empty
    if not campaign_data.bolna_agent_id:
        raise HTTPException(
            status_code=400,
            detail="Bolna agent ID required"
        )

    # 🔹 Validate agent from Bolna
    agent = await get_agent_details(campaign_data.bolna_agent_id)

    if not agent:
        raise HTTPException(
            status_code=400,
            detail="Invalid Bolna agent ID"
        )
    
    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        organization_id=current_user.organization_id,
        bolna_agent_id=campaign_data.bolna_agent_id
    )

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    return campaign

@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    stmt = select(Campaign).where(
        Campaign.organization_id == current_user.organization_id
    )

    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    return campaigns

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id
    )

    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign

@router.get("/{campaign_id}/agent")
async def get_campaign_agent(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id
    )

    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not campaign.bolna_agent_id:
        raise HTTPException(status_code=400, detail="No agent linked")

    agent_data = await get_agent_details(campaign.bolna_agent_id)

    return agent_data

@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign_endpoint(
    campaign: Campaign = Depends(get_authorized_campaign),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_balance = await has_sufficient_balance(
        str(current_user.organization_id), db
    )

    if not has_balance:
        balance = await get_balance(
            str(current_user.organization_id), db
        )
        raise HTTPException(
            status_code=402,  # 402 = Payment Required
            detail={
                "error": "Insufficient balance",
                "message": "Your wallet has 0 minutes. Please recharge to start campaign.",
                "minutes_balance": balance["minutes_balance"],
                "rate_per_minute": balance["rate_per_minute"],
            }
        )
    return await start_campaign(db, campaign.id)


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign_endpoint(
    campaign: Campaign = Depends(get_authorized_campaign),
    db: AsyncSession = Depends(get_db),
):
    return await pause_campaign(db, campaign.id)


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign_endpoint(
    campaign: Campaign = Depends(get_authorized_campaign),
    db: AsyncSession = Depends(get_db),
):
    return await resume_campaign(db, campaign.id)


@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
async def stop_campaign_endpoint(
    campaign: Campaign = Depends(get_authorized_campaign),
    db: AsyncSession = Depends(get_db),
):
    return await stop_campaign(db, campaign.id)

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id
    )

    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # remove any call logs tied to this campaign first to avoid FK violations
    await db.execute(delete(CallLog).where(CallLog.campaign_id == campaign.id))
    await db.delete(campaign)
    await db.commit()

    return {"message": "Campaign deleted successfully"}