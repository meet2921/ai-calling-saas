from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.call_logs import CallLog


async def get_campaign_analytics(db: AsyncSession, campaign_id):

    total_executions = (
        await db.scalar(
            select(func.count(CallLog.id))
            .where(CallLog.campaign_id == campaign_id)
        )
    ) or 0

    total_duration = (
        await db.scalar(
            select(func.coalesce(func.sum(CallLog.duration), 0))
            .where(CallLog.campaign_id == campaign_id)
        )
    ) or 0

    total_cost = (
        await db.scalar(
            select(func.coalesce(func.sum(CallLog.cost), 0))
            .where(CallLog.campaign_id == campaign_id)
        )
    ) or 0

    avg_duration = (
        await db.scalar(
            select(func.coalesce(func.avg(CallLog.duration), 0))
            .where(CallLog.campaign_id == campaign_id)
        )
    ) or 0

    avg_cost = (
        await db.scalar(
            select(func.coalesce(func.avg(CallLog.cost), 0))
            .where(CallLog.campaign_id == campaign_id)
        )
    ) or 0

    return {
        "total_executions": total_executions,
        "total_duration": float(total_duration),
        "total_cost": float(total_cost),
        "avg_duration": round(float(avg_duration), 2),
        "avg_cost": round(float(avg_cost), 4),
    }