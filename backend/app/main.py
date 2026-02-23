from fastapi import FastAPI
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaign_router
from app.api.v1.lead import router as lead_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(campaign_router)
app.include_router(lead_router)