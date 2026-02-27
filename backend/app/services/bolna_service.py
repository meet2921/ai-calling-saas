import httpx
import os
import requests
from app.core.config import settings
from dotenv import load_dotenv
load_dotenv()

from starlette.exceptions import HTTPException

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")
BOLNA_BASE_URL = os.getenv("BOLNA_API_URL", "https://api.bolna.ai/v2")
BOLNA_MAKE_CALL_URL = os.getenv("BOLNAMAKE_CALL_URL", "https://api.bolna.ai")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://matrilineal-hipshot-charlyn.ngrok-free.dev")
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