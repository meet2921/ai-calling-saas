from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.api.v1.auth      import router as auth_router
from app.api.v1.campaigns  import router as campaign_router
from app.api.v1.lead       import router as lead_router
from app.api.v1.webhook    import router as webhook_router
from app.api.v1.analytics  import router as analytics_router
from app.api.v1.admin      import router as admin_router
from app.api.v1.wallet     import router as wallet_router

app = FastAPI(
    title="AI Calling SaaS",
    docs_url="/api/docs",
    description="Multi-tenant AI calling platform. /admin/* requires Super Admin token.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,     prefix="/api/v1/auth")     # /api/v1/auth/*
app.include_router(campaign_router, prefix="/api/v1/campaigns")# /api/v1/campaigns/*
app.include_router(lead_router,     prefix="/api/v1")          # /api/v1/campaigns/{id}/leads/*
app.include_router(webhook_router,  prefix="/api/v1")          # /api/v1/bolna/webhook
app.include_router(analytics_router,prefix="/api/v1")          # /api/v1/campaigns/{id}/analytics
app.include_router(wallet_router,   prefix="/api/v1")          # /api/v1/wallet/*
app.include_router(admin_router)                               # /api/v1/admin/* (already has full prefix)

@app.get("/health")
def health():
    return {"status": "ok"}
