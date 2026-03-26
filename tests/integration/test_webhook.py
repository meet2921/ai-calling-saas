"""
BLACK BOX — POST /api/v1/bolna/webhook

Tests token verification, payload parsing, and call log handling:
valid/invalid tokens, empty body, unknown call IDs, lead status updates.
"""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.lead import LeadStatus
from tests.conftest import ORG_ID, CAMP_ID, LEAD_ID

WEBHOOK_URL = "/api/v1/bolna/webhook"
VALID_TOKEN = "test-webhook-secret-token"


def _payload(call_id=None, status="completed", duration=90, phone="9876543210"):
    return {
        "call_id":               call_id or str(uuid.uuid4()),
        "status":                status,
        "conversation_duration": duration,
        "user_number":           phone,
        "metadata": {
            "lead_id":     str(LEAD_ID),
            "campaign_id": str(CAMP_ID),
        },
    }


def _make_lead(status=LeadStatus.CALLING):
    lead = MagicMock()
    lead.id              = LEAD_ID
    lead.campaign_id     = CAMP_ID
    lead.organization_id = ORG_ID
    lead.phone           = "9876543210"
    lead.status          = status
    lead.external_call_id = None
    return lead


def _make_call_log(call_id=None):
    log = MagicMock()
    log.id              = uuid.uuid4()
    log.external_call_id = call_id or str(uuid.uuid4())
    log.campaign_id     = CAMP_ID
    log.lead_id         = LEAD_ID
    log.duration        = 0
    log.cost            = 0.0
    log.status          = "initiated"
    return log


def _make_campaign():
    c = MagicMock()
    c.id              = CAMP_ID
    c.organization_id = ORG_ID
    return c


# ─── Token verification ───────────────────────────────────────────────────────

class TestWebhookTokenVerification:

    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self, client, mock_db):
        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = VALID_TOKEN

            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps(_payload()).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_returns_401(self, client, mock_db):
        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = VALID_TOKEN

            resp = await client.post(
                f"{WEBHOOK_URL}?token=wrong-token",
                content=json.dumps(_payload()).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_correct_token_does_not_return_401(self, client, mock_db):
        lead    = _make_lead()
        call_log = _make_call_log()
        mock_db.get.return_value = lead
        mock_db.execute.return_value.scalar_one_or_none.return_value = call_log

        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = VALID_TOKEN
            with patch("app.api.v1.webhook.deduct_minutes_for_call", new_callable=AsyncMock):
                resp = await client.post(
                    f"{WEBHOOK_URL}?token={VALID_TOKEN}",
                    content=json.dumps(_payload()).encode(),
                    headers={"Content-Type": "application/json"},
                )
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_skips_verification_when_secret_not_set(self, client, mock_db):
        """When BOLNA_WEBHOOK_SECRET is empty, verification is skipped (dev mode)."""
        lead    = _make_lead()
        mock_db.get.return_value = lead
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = ""   # not set
            with patch("app.api.v1.webhook.deduct_minutes_for_call", new_callable=AsyncMock):
                resp = await client.post(
                    WEBHOOK_URL,
                    content=json.dumps(_payload()).encode(),
                    headers={"Content-Type": "application/json"},
                )
        assert resp.status_code != 401


# ─── Payload handling ─────────────────────────────────────────────────────────

class TestWebhookPayload:

    @pytest.mark.asyncio
    async def test_empty_body_returns_ignored(self, client, mock_db):
        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = ""

            resp = await client.post(
                WEBHOOK_URL,
                content=b"",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client, mock_db):
        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = ""

            resp = await client.post(
                WEBHOOK_URL,
                content=b"not json at all",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_call_id_returns_ignored(self, client, mock_db):
        payload = {"status": "completed", "duration": 90}   # no call_id
        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = ""

            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert "ignored" in resp.json()["status"]

    @pytest.mark.asyncio
    async def test_non_call_event_returns_ignored(self, client, mock_db):
        payload = {"event": "agent.updated", "data": {}}
        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = ""

            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_completed_call_deducts_wallet_minutes(self, client, mock_db):
        lead    = _make_lead()
        call_log = _make_call_log()
        mock_db.get.return_value = lead
        mock_db.execute.return_value.scalar_one_or_none.return_value = call_log

        with patch("app.api.v1.webhook.settings") as mock_settings:
            mock_settings.BOLNA_WEBHOOK_SECRET = ""
            with patch("app.api.v1.webhook.deduct_minutes_for_call", new_callable=AsyncMock) as mock_deduct:
                mock_deduct.return_value = {"minutes_deducted": 2, "new_balance": 98}

                resp = await client.post(
                    WEBHOOK_URL,
                    content=json.dumps(_payload(status="completed", duration=90)).encode(),
                    headers={"Content-Type": "application/json"},
                )

        assert resp.status_code == 200
        mock_deduct.assert_called_once()
