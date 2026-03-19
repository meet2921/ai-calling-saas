from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db
from app.services.analytics_service import get_campaign_analytics
from app.models.call_logs import CallLog
from app.models.campaigns import Campaign
from app.models.user import User
from app.core.deps import get_current_user
from sqlalchemy.future import select
from fastapi import HTTPException

router = APIRouter()


@router.get("/campaigns/{campaign_id}/analytics")
async def campaign_analytics(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify campaign belongs to user's org
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")

    return await get_campaign_analytics(db, campaign_id)


@router.get("/campaigns/{campaign_id}/logs")
async def campaign_logs(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify campaign belongs to user's org
    campaign_result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id,
        )
    )
    if not campaign_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await db.execute(
        select(CallLog).where(CallLog.campaign_id == campaign_id)
    )
    logs = result.scalars().all()

    return logs