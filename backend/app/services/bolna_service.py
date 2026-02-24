import httpx
import os
from dotenv import load_dotenv
load_dotenv()

from starlette.exceptions import HTTPException

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")
BOLNA_BASE_URL = os.getenv("BOLNA_API_URL", "https://api.bolna.ai/v2")

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