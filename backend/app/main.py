from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaign_router
from app.api.v1.lead import router as lead_router
from app.api.v1.webhook import router as webhook_router
from app.api.v1.analytics import router as analytics_router
# from app.api.v1.user import router as user_router  # Fixed import
from app.api.v1.wallet import router as wallet_router
from app.api.v1.admin import router as admin_router
from app.core.config import settings
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Calling SaaS", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Apply the prefix to EVERYTHING for consistency
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(campaign_router, prefix="/api/v1/campaigns", tags=["Campaigns"])
# app.include_router(user_router, prefix="/api/v1/users", tags=["Users"]) # Added this
app.include_router(lead_router, prefix="/api/v1", tags=["Leads"])
app.include_router(webhook_router, prefix="/api/v1", tags=["Webhook"])
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
app.include_router(wallet_router, prefix="/api/v1", tags=["Wallet"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Super Admin"])

@app.get("/health")
def health():
    return {"status": "ok"}