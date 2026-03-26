"""
BLACK BOX — /api/v1/campaigns/*

Tests campaign CRUD and lifecycle endpoints: create, list, get,
start (balance + lead checks), pause, resume, stop, delete, update.
"""

import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.campaigns import CampaignStatus
from tests.conftest import ORG_ID, CAMP_ID


def _make_campaign(status=CampaignStatus.draft, is_processing=False):
    c = MagicMock()
    c.id              = CAMP_ID
    c.name            = "Test Campaign"
    c.description     = "Desc"
    c.organization_id = ORG_ID
    c.bolna_agent_id  = "agent-abc"
    c.status          = status
    c.is_processing   = is_processing
    c.created_at      = "2024-01-01T00:00:00"
    c.updated_at      = "2024-01-01T00:00:00"
    return c


# ─── POST /campaigns/ ─────────────────────────────────────────────────────────

class TestCreateCampaign:

    @pytest.mark.asyncio
    @patch("app.api.v1.campaigns.get_agent_details", new_callable=AsyncMock)
    async def test_creates_campaign_successfully(self, mock_agent, auth_client, mock_db):
        mock_agent.return_value = {"agent_id": "agent-abc", "name": "Test Agent"}
        campaign = _make_campaign()
        def _set_defaults(c):
            c.id         = CAMP_ID
            c.status     = CampaignStatus.draft
            c.created_at = datetime(2024, 1, 1)
            c.updated_at = None
        mock_db.refresh = AsyncMock(side_effect=_set_defaults)

        resp = await auth_client.post("/api/v1/campaigns/", json={
            "name":           "Test Campaign",
            "description":    "Desc",
            "bolna_agent_id": "agent-abc",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_bolna_agent_id_returns_400(self, auth_client):
        resp = await auth_client.post("/api/v1/campaigns/", json={
            "name":        "No Agent Campaign",
            "description": "Desc",
        })
        assert resp.status_code == 400
        assert "agent" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_403(self, client):
        resp = await client.post("/api/v1/campaigns/", json={
            "name":           "Camp",
            "bolna_agent_id": "agent-abc",
        })
        assert resp.status_code in (401, 403)


# ─── GET /campaigns/ ──────────────────────────────────────────────────────────

class TestListCampaigns:

    @pytest.mark.asyncio
    async def test_returns_list_of_campaigns(self, auth_client, mock_db):
        campaigns = [_make_campaign(), _make_campaign()]
        mock_db.execute.return_value.scalars.return_value.all.return_value = campaigns

        resp = await auth_client.get("/api/v1/campaigns/")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_campaigns(self, auth_client, mock_db):
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        resp = await auth_client.get("/api/v1/campaigns/")

        assert resp.status_code == 200
        assert resp.json() == []


# ─── GET /campaigns/{id} ──────────────────────────────────────────────────────

class TestGetCampaign:

    @pytest.mark.asyncio
    async def test_returns_campaign_by_id(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        resp = await auth_client.get(f"/api/v1/campaigns/{CAMP_ID}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_id(self, auth_client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await auth_client.get(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert resp.status_code == 404


# ─── POST /campaigns/{id}/start ───────────────────────────────────────────────

class TestStartCampaign:

    @pytest.mark.asyncio
    @patch("app.api.v1.campaigns.has_sufficient_balance", new_callable=AsyncMock)
    @patch("app.api.v1.campaigns.start_campaign", new_callable=AsyncMock)
    async def test_returns_402_when_no_balance(self, mock_start, mock_balance, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign
        mock_balance.return_value = False

        balance_result = MagicMock()
        balance_result.__getitem__ = lambda self, k: 0 if k == "minutes_balance" else 0.5

        with patch("app.api.v1.campaigns.get_balance", new_callable=AsyncMock) as mock_get_balance:
            mock_get_balance.return_value = {"minutes_balance": 0, "rate_per_minute": 0.5}
            resp = await auth_client.post(f"/api/v1/campaigns/{CAMP_ID}/start")

        assert resp.status_code == 402

    @pytest.mark.asyncio
    @patch("app.api.v1.campaigns.has_sufficient_balance", new_callable=AsyncMock)
    async def test_returns_400_when_no_leads(self, mock_balance, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": campaign}),  # get_authorized_campaign
            MagicMock(**{"scalar.return_value": 0}),                     # lead_count check
        ]
        mock_balance.return_value = True

        resp = await auth_client.post(f"/api/v1/campaigns/{CAMP_ID}/start")
        assert resp.status_code == 400
        assert "leads" in resp.json()["detail"].lower()


# ─── POST /campaigns/{id}/pause ───────────────────────────────────────────────

class TestPauseCampaign:

    @pytest.mark.asyncio
    @patch("app.api.v1.campaigns.pause_campaign", new_callable=AsyncMock)
    async def test_pause_running_campaign(self, mock_pause, auth_client, mock_db):
        campaign = _make_campaign(CampaignStatus.running)
        paused   = _make_campaign(CampaignStatus.paused)
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign
        mock_pause.return_value = paused

        resp = await auth_client.post(f"/api/v1/campaigns/{CAMP_ID}/pause")
        assert resp.status_code == 200


# ─── POST /campaigns/{id}/stop ────────────────────────────────────────────────

class TestStopCampaign:

    @pytest.mark.asyncio
    @patch("app.api.v1.campaigns.stop_campaign", new_callable=AsyncMock)
    async def test_stop_campaign(self, mock_stop, auth_client, mock_db):
        campaign = _make_campaign(CampaignStatus.running)
        stopped  = _make_campaign(CampaignStatus.stopped)
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign
        mock_stop.return_value = stopped

        resp = await auth_client.post(f"/api/v1/campaigns/{CAMP_ID}/stop")
        assert resp.status_code == 200


# ─── DELETE /campaigns/{id} ───────────────────────────────────────────────────

class TestDeleteCampaign:

    @pytest.mark.asyncio
    async def test_deletes_existing_campaign(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        resp = await auth_client.delete(f"/api/v1/campaigns/{CAMP_ID}")

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_campaign(self, auth_client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await auth_client.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert resp.status_code == 404


# ─── PUT /campaigns/{id}/update ───────────────────────────────────────────────

class TestUpdateCampaign:

    @pytest.mark.asyncio
    @patch("app.api.v1.campaigns.get_agent_details", new_callable=AsyncMock)
    async def test_updates_campaign_fields(self, mock_agent, auth_client, mock_db):
        campaign = _make_campaign()
        mock_agent.return_value = {"agent_id": "new-agent"}
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        resp = await auth_client.put(f"/api/v1/campaigns/{CAMP_ID}/update", json={
            "name":           "Updated Name",
            "description":    "Updated Desc",
            "bolna_agent_id": "new-agent",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_bolna_agent_id_returns_400(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        resp = await auth_client.put(f"/api/v1/campaigns/{CAMP_ID}/update", json={
            "name":        "Updated Name",
            "description": "Desc",
        })
        assert resp.status_code == 400
