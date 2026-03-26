"""
WHITE BOX — app/services/analytics_service.py

Tests the aggregation logic: correct counts, sums, averages,
and graceful handling of campaigns with no call logs.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from app.services.analytics_service import get_campaign_analytics


def _db_with_scalars(*values):
    """
    Returns a mock db whose .scalar() calls return values in order.
    get_campaign_analytics calls db.scalar() 5 times:
      total_executions, total_duration, total_cost, avg_duration, avg_cost
    """
    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=list(values))
    return db


class TestGetCampaignAnalytics:

    @pytest.mark.asyncio
    async def test_returns_zeros_for_empty_campaign(self):
        db = _db_with_scalars(0, 0, 0, 0, 0)
        result = await get_campaign_analytics(db, uuid.uuid4())

        assert result["total_executions"] == 0
        assert result["total_duration"]   == 0.0
        assert result["total_cost"]       == 0.0
        assert result["avg_duration"]     == 0.0
        assert result["avg_cost"]         == 0.0

    @pytest.mark.asyncio
    async def test_returns_correct_totals(self):
        db = _db_with_scalars(10, 600, 5.50, 60.0, 0.55)
        result = await get_campaign_analytics(db, uuid.uuid4())

        assert result["total_executions"] == 10
        assert result["total_duration"]   == 600.0
        assert result["total_cost"]       == 5.50

    @pytest.mark.asyncio
    async def test_rounds_avg_duration_to_2_decimals(self):
        # avg_duration = 61.666... → 61.67
        db = _db_with_scalars(3, 185, 3.0, 61.6667, 1.0)
        result = await get_campaign_analytics(db, uuid.uuid4())
        assert result["avg_duration"] == 61.67

    @pytest.mark.asyncio
    async def test_rounds_avg_cost_to_4_decimals(self):
        # avg_cost = 0.33333... → 0.3333
        db = _db_with_scalars(3, 180, 1.0, 60.0, 0.33333)
        result = await get_campaign_analytics(db, uuid.uuid4())
        assert result["avg_cost"] == 0.3333

    @pytest.mark.asyncio
    async def test_handles_none_values_from_db(self):
        # coalesce in SQL returns 0, but test None handling too
        db = _db_with_scalars(None, None, None, None, None)
        result = await get_campaign_analytics(db, uuid.uuid4())

        assert result["total_executions"] == 0
        assert result["total_duration"]   == 0.0
        assert result["total_cost"]       == 0.0

    @pytest.mark.asyncio
    async def test_result_keys_are_present(self):
        db = _db_with_scalars(5, 300, 2.5, 60.0, 0.5)
        result = await get_campaign_analytics(db, uuid.uuid4())

        assert "total_executions" in result
        assert "total_duration"   in result
        assert "total_cost"       in result
        assert "avg_duration"     in result
        assert "avg_cost"         in result
