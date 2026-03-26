"""
WHITE BOX — app/services/campaign_service.py

Tests every state transition and error condition for the campaign lifecycle:
draft → running → paused → running → stopped / completed.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.campaign_service import (
    get_campaign_or_404,
    start_campaign,
    pause_campaign,
    resume_campaign,
    stop_campaign,
)
from app.models.campaigns import CampaignStatus


def _mock_campaign(status=CampaignStatus.draft, is_processing=False):
    c = MagicMock()
    c.id            = uuid.uuid4()
    c.status        = status
    c.is_processing = is_processing
    c.updated_at    = None
    return c


def _db_with_campaign(campaign):
    result = MagicMock()
    result.scalar_one_or_none.return_value = campaign
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    db.commit  = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ─── get_campaign_or_404 ──────────────────────────────────────────────────────

class TestGetCampaignOr404:

    @pytest.mark.asyncio
    async def test_returns_campaign_when_found(self):
        campaign = _mock_campaign()
        db = _db_with_campaign(campaign)
        result = await get_campaign_or_404(db, campaign.id)
        assert result is campaign

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        db = _db_with_campaign(None)
        with pytest.raises(HTTPException) as exc:
            await get_campaign_or_404(db, uuid.uuid4())
        assert exc.value.status_code == 404


# ─── start_campaign ───────────────────────────────────────────────────────────

class TestStartCampaign:

    @pytest.mark.asyncio
    @patch("app.services.campaign_service.process_campaign")
    async def test_starts_from_draft(self, mock_task):
        mock_task.apply_async = MagicMock()
        campaign = _mock_campaign(CampaignStatus.draft)
        db = _db_with_campaign(campaign)

        result = await start_campaign(db, campaign.id)

        assert result.status        == CampaignStatus.running
        assert result.is_processing is True
        mock_task.apply_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.campaign_service.process_campaign")
    async def test_starts_from_paused(self, mock_task):
        mock_task.apply_async = MagicMock()
        campaign = _mock_campaign(CampaignStatus.paused)
        db = _db_with_campaign(campaign)

        result = await start_campaign(db, campaign.id)
        assert result.status == CampaignStatus.running

    @pytest.mark.asyncio
    async def test_raises_400_when_already_running(self):
        campaign = _mock_campaign(CampaignStatus.running)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await start_campaign(db, campaign.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_400_when_already_processing(self):
        campaign = _mock_campaign(CampaignStatus.draft, is_processing=True)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await start_campaign(db, campaign.id)
        assert exc.value.status_code == 400
        assert "already processing" in exc.value.detail.lower()


# ─── pause_campaign ───────────────────────────────────────────────────────────

class TestPauseCampaign:

    @pytest.mark.asyncio
    async def test_pauses_running_campaign(self):
        campaign = _mock_campaign(CampaignStatus.running)
        db = _db_with_campaign(campaign)

        result = await pause_campaign(db, campaign.id)
        assert result.status == CampaignStatus.paused

    @pytest.mark.asyncio
    async def test_raises_400_when_not_running(self):
        campaign = _mock_campaign(CampaignStatus.draft)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await pause_campaign(db, campaign.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_400_when_already_paused(self):
        campaign = _mock_campaign(CampaignStatus.paused)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await pause_campaign(db, campaign.id)
        assert exc.value.status_code == 400


# ─── resume_campaign ──────────────────────────────────────────────────────────

class TestResumeCampaign:

    @pytest.mark.asyncio
    @patch("app.services.campaign_service.process_campaign")
    async def test_resumes_paused_campaign(self, mock_task):
        mock_task.delay = MagicMock()
        campaign = _mock_campaign(CampaignStatus.paused)
        db = _db_with_campaign(campaign)

        result = await resume_campaign(db, campaign.id)
        assert result.status == CampaignStatus.running
        mock_task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_400_when_not_paused(self):
        campaign = _mock_campaign(CampaignStatus.running)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await resume_campaign(db, campaign.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_400_when_draft(self):
        campaign = _mock_campaign(CampaignStatus.draft)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await resume_campaign(db, campaign.id)
        assert exc.value.status_code == 400


# ─── stop_campaign ────────────────────────────────────────────────────────────

class TestStopCampaign:

    @pytest.mark.asyncio
    async def test_stops_running_campaign(self):
        campaign = _mock_campaign(CampaignStatus.running)
        db = _db_with_campaign(campaign)

        result = await stop_campaign(db, campaign.id)
        assert result.status == CampaignStatus.stopped

    @pytest.mark.asyncio
    async def test_stops_paused_campaign(self):
        campaign = _mock_campaign(CampaignStatus.paused)
        db = _db_with_campaign(campaign)

        result = await stop_campaign(db, campaign.id)
        assert result.status == CampaignStatus.stopped

    @pytest.mark.asyncio
    async def test_raises_400_when_already_stopped(self):
        campaign = _mock_campaign(CampaignStatus.stopped)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await stop_campaign(db, campaign.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_400_when_already_completed(self):
        campaign = _mock_campaign(CampaignStatus.completed)
        db = _db_with_campaign(campaign)

        with pytest.raises(HTTPException) as exc:
            await stop_campaign(db, campaign.id)
        assert exc.value.status_code == 400
