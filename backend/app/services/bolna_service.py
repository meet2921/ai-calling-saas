import httpx
import os
import requests
from app.core.config import settings
from dotenv import load_dotenv
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
    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BOLNA_BASE_URL}/agent/{agent_id}",
            headers=headers
        )

    if response.status_code != 200: 
        raise HTTPException(
            status_code=400,
            detail=f"Bolna error: {response.text}"
        )

    return response.json()

def make_call(
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

    response = httpx.post(
        f"{BOLNA_MAKE_CALL_URL}/call",
        headers=headers,
        json=payload,
        timeout=20
    )

    print("\n========== BOLNA DEBUG ==========")
    print("Status Code:", response.status_code)
    print("Response Body:", response.text)
    print("Payload Sent:", payload)
    print("=================================\n")

    if response.status_code >= 400:
        raise Exception(f"Bolna error: {response.text}")

    return response.json()