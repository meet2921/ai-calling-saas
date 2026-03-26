"""
BLACK BOX — /api/v1/campaigns/{id}/leads/*

Tests lead upload (CSV parsing, duplicate detection, invalid files),
listing with pagination/filtering, deletion, and status retrieval.
"""

import io
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.lead import LeadStatus
from app.models.campaigns import CampaignStatus
from tests.conftest import ORG_ID, CAMP_ID, LEAD_ID


def _make_campaign(status=CampaignStatus.draft):
    c = MagicMock()
    c.id              = CAMP_ID
    c.organization_id = ORG_ID
    c.status          = status
    return c


def _make_lead(phone="9876543210", status=LeadStatus.PENDING):
    lead = MagicMock()
    lead.id           = LEAD_ID
    lead.phone        = phone
    lead.status       = status
    lead.custom_fields = {}
    lead.created_at   = MagicMock(isoformat=lambda: "2024-01-01T00:00:00")
    return lead


def _csv_bytes(content: str) -> bytes:
    return content.encode("utf-8")


# ─── POST /campaigns/{id}/leads/upload ───────────────────────────────────────

class TestUploadLeads:

    @pytest.mark.asyncio
    async def test_valid_csv_uploads_leads(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        csv_content = _csv_bytes("phone,name\n9876543210,Alice\n9876543211,Bob\n")

        resp = await auth_client.post(
            f"/api/v1/campaigns/{CAMP_ID}/leads/upload",
            files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_uploaded"] == 2

    @pytest.mark.asyncio
    async def test_missing_phone_column_returns_400(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        csv_content = _csv_bytes("name,email\nAlice,alice@test.com\n")

        resp = await auth_client.post(
            f"/api/v1/campaigns/{CAMP_ID}/leads/upload",
            files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        )

        assert resp.status_code == 400
        assert "phone" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_empty_csv_returns_no_leads_message(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        csv_content = _csv_bytes("phone\n")   # header only, no rows

        resp = await auth_client.post(
            f"/api/v1/campaigns/{CAMP_ID}/leads/upload",
            files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        )

        assert resp.status_code == 200
        assert "no valid leads" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_duplicate_phones_in_file_are_deduplicated(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign

        # Same phone appears twice in file
        csv_content = _csv_bytes("phone\n9876543210\n9876543210\n")

        resp = await auth_client.post(
            f"/api/v1/campaigns/{CAMP_ID}/leads/upload",
            files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        )

        assert resp.status_code == 200
        assert resp.json()["total_uploaded"] == 1   # only one kept

    @pytest.mark.asyncio
    async def test_campaign_not_found_returns_404(self, auth_client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        csv_content = _csv_bytes("phone\n9876543210\n")

        resp = await auth_client.post(
            f"/api/v1/campaigns/{uuid.uuid4()}/leads/upload",
            files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_db_duplicate_constraint_returns_400(self, auth_client, mock_db):
        campaign = _make_campaign()
        mock_db.execute.return_value.scalar_one_or_none.return_value = campaign
        mock_db.commit.side_effect = Exception("Duplicate phone constraint")

        csv_content = _csv_bytes("phone\n9876543210\n")

        resp = await auth_client.post(
            f"/api/v1/campaigns/{CAMP_ID}/leads/upload",
            files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 400


# ─── GET /campaigns/{id}/leads ───────────────────────────────────────────────

class TestListLeads:

    @pytest.mark.asyncio
    async def test_returns_paginated_leads(self, auth_client, mock_db):
        leads = [_make_lead("9876543210"), _make_lead("9876543211")]
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": _make_campaign()}),  # campaign lookup
            MagicMock(**{"scalars.return_value.all.return_value": leads}),       # leads query
        ]

        resp = await auth_client.get(f"/api/v1/campaigns/{CAMP_ID}/leads")

        assert resp.status_code == 200
        body = resp.json()
        assert "leads"     in body
        assert "page"      in body
        assert "page_size" in body

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_leads(self, auth_client, mock_db):
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": _make_campaign()}),
            MagicMock(**{"scalars.return_value.all.return_value": []}),
        ]

        resp = await auth_client.get(f"/api/v1/campaigns/{CAMP_ID}/leads")

        assert resp.status_code == 200
        assert resp.json()["leads"] == []

    @pytest.mark.asyncio
    async def test_campaign_not_found_returns_404(self, auth_client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await auth_client.get(f"/api/v1/campaigns/{uuid.uuid4()}/leads")
        assert resp.status_code == 404


# ─── DELETE /campaigns/{id}/leads/{lead_id} ──────────────────────────────────

class TestDeleteLead:

    @pytest.mark.asyncio
    async def test_deletes_existing_lead(self, auth_client, mock_db):
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": _make_campaign()}),  # campaign
            MagicMock(**{"fetchone.return_value": (LEAD_ID,)}),                  # delete returning
        ]

        resp = await auth_client.delete(f"/api/v1/campaigns/{CAMP_ID}/leads/{LEAD_ID}")

        assert resp.status_code == 200
        assert "removed" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_lead(self, auth_client, mock_db):
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": _make_campaign()}),
            MagicMock(**{"fetchone.return_value": None}),
        ]

        resp = await auth_client.delete(f"/api/v1/campaigns/{CAMP_ID}/leads/{uuid.uuid4()}")
        assert resp.status_code == 404


# ─── GET /campaigns/{id}/leads/{lead_id}/lead-status ─────────────────────────

class TestGetLeadStatus:

    @pytest.mark.asyncio
    async def test_returns_lead_status(self, auth_client, mock_db):
        lead = _make_lead(status=LeadStatus.COMPLETED)
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": _make_campaign()}),
            MagicMock(**{"scalar_one_or_none.return_value": lead}),
        ]

        resp = await auth_client.get(
            f"/api/v1/campaigns/{CAMP_ID}/leads/{LEAD_ID}/lead-status"
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == LeadStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_lead(self, auth_client, mock_db):
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": _make_campaign()}),
            MagicMock(**{"scalar_one_or_none.return_value": None}),
        ]

        resp = await auth_client.get(
            f"/api/v1/campaigns/{CAMP_ID}/leads/{uuid.uuid4()}/lead-status"
        )
        assert resp.status_code == 404
