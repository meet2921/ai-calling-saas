import httpx
import os
import requests
from app.core.config import settings
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.call_logs import CallLog
from app.models.lead import Lead
from dotenv import load_dotenv
from httpx import Client

load_dotenv()

from fastapi import HTTPException

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")
BOLNA_BASE_URL = os.getenv("BOLNA_API_URL")
BOLNA_MAKE_CALL_URL = os.getenv("BOLNAMAKE_CALL_URL")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")


def _extract_call_id(data):
    if not data:
        return None

    if isinstance(data, dict):
        for key in ("id", "call_id", "execution_id", "run_id"):
            val = data.get(key)
            if val:
                return val

        for parent in ("data", "call", "result"):
            nested = data.get(parent)
            if isinstance(nested, dict):
                for key in ("id", "call_id", "execution_id", "run_id"):
                    val = nested.get(key)
                    if val:
                        return val

        for list_key in ("calls",):
            lst = data.get(list_key)
            if isinstance(lst, list) and lst:
                first = lst[0]
                if isinstance(first, dict):
                    for key in ("id", "call_id", "execution_id", "run_id"):
                        val = first.get(key)
                        if val:
                            return val

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ("id", "call_id", "execution_id", "run_id"):
                val = first.get(key)
                if val:
                    return val

    return None


# ─────────────────────────────────────────────────────────────────────────────
# ASYNC — used by FastAPI routes (campaigns router, etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def get_agent_details(agent_id: str):
    """
    Fetch details for a Bolna agent.
    Called from FastAPI routes — uses async httpx.
    """
    if not BOLNA_API_KEY:
        raise HTTPException(status_code=500, detail="Bolna API key is not set")

    headers = {"Authorization": f"Bearer {BOLNA_API_KEY}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BOLNA_BASE_URL}/agent/{agent_id}",
            headers=headers,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Bolna error: {response.text}",
        )

    return response.json()


# ─────────────────────────────────────────────────────────────────────────────
# SYNC — used by Celery tasks only
# Accepts sqlalchemy.orm.Session (sync), NOT AsyncSession
# ─────────────────────────────────────────────────────────────────────────────

def make_call(
    db: Session,           # ← correct type: sync SQLAlchemy Session
    phone: str,
    agent_id: str,
    campaign_id: str,
    lead_id: str,
) -> dict:
    """
    Initiates a call via Bolna API and immediately creates a CallLog row.
    This is a SYNC function — only call it from Celery tasks, never from
    async FastAPI routes.
    """
    if not BOLNA_API_KEY:
        raise Exception("Bolna API key is not set")

    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "agent_id": agent_id,
        "recipient_phone_number": phone,
        "webhook_url": f"{WEBHOOK_BASE_URL}/api/v1/bolna/webhook",
        "metadata": {
            "campaign_id": str(campaign_id),
            "lead_id": str(lead_id),
        },
    }

    # Sync HTTP call — correct inside a Celery worker
    with Client(timeout=20) as client:
        response = client.post(
            f"{BOLNA_MAKE_CALL_URL}/call",
            headers=headers,
            json=payload,
        )

    if response.status_code >= 400:
        raise Exception(f"Bolna error: {response.text}")

    try:
        data = response.json()
    except ValueError:
        raise Exception(f"Bolna returned non-JSON response: {response.text}")

    call_id = _extract_call_id(data)

    if not call_id:
        raise Exception(f"Bolna did not return call_id. Response: {response.text}")

    # Update Lead with external_call_id
    # db.get() is correct for sync Session — this was the core bug
    lead = db.get(Lead, lead_id)
    if lead:
        lead.external_call_id = call_id

    # Create CallLog immediately so webhook can find it by call_id
    call_log = CallLog(
        external_call_id=call_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        user_number=phone,
        status="initiated",
        created_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
    )

    db.add(call_log)
    db.flush()   # INSERT immediately, within same transaction
    db.commit()  # commit so webhook can read this row from its own session

    return data