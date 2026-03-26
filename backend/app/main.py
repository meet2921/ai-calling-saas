from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
import logging
import os

from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaign_router
from app.api.v1.lead import router as lead_router
from app.api.v1.webhook import router as webhook_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.wallet import router as wallet_router
from app.api.v1.admin import router as admin_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import engine, get_redis_pool
from dotenv import load_dotenv

load_dotenv()

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("call_logs.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI(title="AI Calling SaaS", docs_url="/docs")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Apply the prefix to EVERYTHING for consistency
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(campaign_router, prefix="/api/v1", tags=["Campaigns"])
app.include_router(lead_router, prefix="/api/v1", tags=["Leads"])
app.include_router(webhook_router, prefix="/api/v1", tags=["Webhook"])
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
app.include_router(wallet_router, prefix="/api/v1", tags=["Wallet"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Super Admin"])

@app.get("/health", tags=["Health"])
async def health():
    status = {"database": "ok", "redis": "ok"}
    http_status = 200

    # ── Database check ────────────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        status["database"] = f"error: {e}"
        http_status = 503

    # ── Redis check ───────────────────────────────────────────────────────────
    try:
        redis = await get_redis_pool()
        await redis.ping()
    except Exception as e:
        status["redis"] = f"error: {e}"
        http_status = 503

    status["status"] = "ok" if http_status == 200 else "degraded"
    return JSONResponse(content=status, status_code=http_status)