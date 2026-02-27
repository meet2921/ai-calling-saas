from fastapi import FastAPI
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaign_router
from app.api.v1.lead import router as lead_router
from app.api.v1.webhook import router as webhook_router
from app.api.v1.analytics import router as analytics_router
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.include_router(auth_router)
app.include_router(campaign_router)
app.include_router(lead_router,prefix="/api/v1", tags=["Leads"])
app.include_router(webhook_router, prefix="/api/v1", tags=["Webhook"])
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])