import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

from app.models.call_logs import CallLog
from app.models.lead import Lead
from app.db.sync_session import SessionLocal

load_dotenv()

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")
BOLNA_BASE_URL = os.getenv("BOLNA_API_URL", "https://api.bolna.ai/v2")
BOLNA_MAKE_CALL_URL = os.getenv("BOLNAMAKE_CALL_URL", "https://api.bolna.ai")
WEBHOOK_BASE_URL = os.getenv(
    "WEBHOOK_BASE_URL",
    "https://unantagonized-morton-twopenny.ngrok-free.dev"
)


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


async def get_agent_details(agent_id: str):
    """Fetch agent details from Bolna by agent ID."""

    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{BOLNA_BASE_URL}/agents/{agent_id}",
            headers=headers,
        )

    if response.status_code >= 400:
        raise Exception(f"Bolna error: {response.text}")

    return response.json()


async def make_call(
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

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.post(
            f"{BOLNA_MAKE_CALL_URL}/call",
            headers=headers,
            json=payload,
        )

    if response.status_code >= 400:
        raise Exception(f"Bolna error: {response.text}")

    data = response.json()

    call_id = _extract_call_id(data)

    if not call_id:
        raise Exception(
            f"Bolna did not return call_id. Response body: {response.text}"
        )

    db = SessionLocal()

    try:

        lead = db.query(Lead).filter(Lead.id == lead_id).first()

        if lead:
            lead.external_call_id = call_id

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
        db.commit()

    finally:
        db.close()

    return {"call_id": call_id}