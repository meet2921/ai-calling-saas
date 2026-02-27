from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db
from app.services.analytics_service import get_campaign_analytics
from app.models.call_logs import CallLog
from app.core.deps import get_current_user
from sqlalchemy.future import select

router = APIRouter()


@router.get("/campaigns/{campaign_id}/analytics")
async def campaign_analytics(
    campaign_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)
):
    return await get_campaign_analytics(db, campaign_id)


@router.get("/campaigns/{campaign_id}/logs")
async def campaign_logs(
    campaign_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(CallLog).where(CallLog.campaign_id == campaign_id)
    )
    logs = result.scalars().all()

    return logs