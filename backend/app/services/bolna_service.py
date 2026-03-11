import httpx
import os
import requests
from app.core.config import settings
from datetime import datetime
from sqlalchemy import select
from app.models.call_logs import CallLog
from app.models.lead import Lead
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from httpx import Client

from app.api.v1 import lead
load_dotenv()

from starlette.exceptions import HTTPException

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")
BOLNA_BASE_URL = os.getenv("BOLNA_API_URL")
BOLNA_MAKE_CALL_URL = os.getenv("BOLNAMAKE_CALL_URL")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")


def _extract_call_id(data):
    if not data:
        return None
    # dict with top-level id (accept execution/run ids as fallbacks)
    if isinstance(data, dict):
        for key in ("id", "call_id", "execution_id", "run_id"):
            val = data.get(key)
            if val:
                return val

        # nested objects commonly named 'data', 'call', or 'result'
        for parent in ("data", "call", "result"):
            nested = data.get(parent)
            if isinstance(nested, dict):
                for key in ("id", "call_id", "execution_id", "run_id"):
                    val = nested.get(key)
                    if val:
                        return val

        # arrays: take first element
        for list_key in ("calls",):
            lst = data.get(list_key)
            if isinstance(lst, list) and lst:
                first = lst[0]
                if isinstance(first, dict):
                    for key in ("id", "call_id", "execution_id", "run_id"):
                        val = first.get(key)
                        if val:
                            return val

    # response may be a list of objects
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ("id", "call_id", "execution_id", "run_id"):
                val = first.get(key)
                if val:
                    return val

    return None
async def get_agent_details(agent_id: str):
    """Fetch details for a Bolna agent.

    The Bolna API will return 404 if the supplied ID does not exist, which is
    the most common reason for failures here. We propagate the original status
    code so callers can distinguish between client and server errors (e.g. a
    missing agent vs. an invalid API key).
    """

    if not BOLNA_API_KEY:
        # early sanity check; avoids sending an empty `Bearer None` header
        raise HTTPException(status_code=500, detail="Bolna API key is not set")

    headers = {"Authorization": f"Bearer {BOLNA_API_KEY}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BOLNA_BASE_URL}/agent/{agent_id}",
            headers=headers,
        )

    if response.status_code != 200:
        # propagate the real status code from Bolna so that a 404 comes back
        # as a 404 to our own client instead of a generic 400, which makes it
        # easier to debug mismatched IDs.
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Bolna error: {response.text}",
        )

    return response.json()

def make_call(
    db: AsyncSession,
    phone: str,
    agent_id: str,
    campaign_id: str,
    lead_id: str,
):

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

    # 🔥 Extract call_id (robustly handle several response shapes)
    call_id = _extract_call_id(data)

    if not call_id:
        raise Exception(f"Bolna did not return call_id. Response body: {response.text}")

    # 🔥 Update Lead with external_call_id
    lead =  db.get(Lead, lead_id)
    if lead:
        lead.external_call_id = call_id

    # 🔥 Create CallLog immediately (CRITICAL)
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
    db.flush()   # ensures INSERT happens immediately
    db.commit()

    return data