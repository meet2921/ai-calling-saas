from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.call_logs import CallLog


async def get_campaign_analytics(db: AsyncSession, campaign_id):

    total_calls = (
        await db.scalar(
            select(func.count(CallLog.id))
            .where(CallLog.campaign_id == campaign_id)
        )
    ) or 0

    completed_calls = (
        await db.scalar(
            select(func.count(CallLog.id))
            .where(
                CallLog.campaign_id == campaign_id,
                CallLog.status.in_(["completed", "call-disconnected"]),
            )
        )
    ) or 0

    failed_calls = (
        await db.scalar(
            select(func.count(CallLog.id))
            .where(
                CallLog.campaign_id == campaign_id,
                CallLog.status.in_(["failed", "busy", "no-answer", "error"]),
            )
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
            .where(CallLog.campaign_id == campaign_id, CallLog.duration > 0)
        )
    ) or 0

    # Per-day breakdown
    daily_rows = (await db.execute(
        select(
            cast(CallLog.executed_at, Date).label("day"),
            func.count(CallLog.id).label("calls"),
            func.coalesce(func.sum(CallLog.duration), 0).label("seconds"),
        )
        .where(CallLog.campaign_id == campaign_id)
        .group_by(cast(CallLog.executed_at, Date))
        .order_by(cast(CallLog.executed_at, Date))
    )).all()

    calls_by_day = [{"date": str(r.day), "calls": r.calls} for r in daily_rows]
    minutes_by_day = [{"date": str(r.day), "minutes": round(r.seconds / 60, 2)} for r in daily_rows]

    # Duration distribution buckets
    buckets = [
        ("0-30s",  0,   30),
        ("30-60s", 30,  60),
        ("1-2min", 60,  120),
        ("2-5min", 120, 300),
        ("5+ min", 300, None),
    ]
    duration_distribution = []
    for label, low, high in buckets:
        q = select(func.count(CallLog.id)).where(
            CallLog.campaign_id == campaign_id,
            CallLog.duration >= low,
        )
        if high is not None:
            q = q.where(CallLog.duration < high)
        count = (await db.scalar(q)) or 0
        duration_distribution.append({"range": label, "calls": count})

    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "failed_calls": failed_calls,
        "total_duration": round(float(total_duration) / 60, 2),
        "avg_duration": round(float(avg_duration), 1),
        "total_cost": float(total_cost),
        "calls_by_day": calls_by_day,
        "minutes_by_day": minutes_by_day,
        "duration_distribution": duration_distribution,
    }