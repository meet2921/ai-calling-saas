from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from uuid import UUID
import csv
import io
import re
from pydantic import BaseModel as _BM
from sqlalchemy import func

from app.db.session import get_db
from app.models.lead import Lead, LeadStatus
from app.models.call_logs import CallLog
from app.models.campaigns import Campaign
from app.core.deps import get_current_user

router = APIRouter()

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

E164_RE = re.compile(r"^\+?[1-9]\d{6,14}$")

def _is_valid_phone(phone: str) -> bool:
    """Basic E.164-style validation. Swap in phonenumbers lib for production."""
    return bool(E164_RE.match(phone.replace(" ", "").replace("-", "")))


async def _get_campaign_or_404(
    campaign_id: UUID,
    organization_id: UUID,
    db: AsyncSession,
) -> Campaign:
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/campaigns/{campaign_id}/leads/upload")
async def upload_leads_csv(
    campaign_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):

    # 1️⃣ Validate campaign belongs to user's organization
    campaign_stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id
    )

    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()     

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 2️⃣ Read CSV file
    contents = await file.read()
    decoded = contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    if "phone" not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain 'phone' column"
        )

    leads_to_insert = []
    phones_seen = set()

    for row in reader:
        phone = row.get("phone")

        if not phone:
            continue

        phone = phone.strip()

        # Remove duplicates inside same file
        if phone in phones_seen:
            continue
        phones_seen.add(phone)

        # Extract custom fields
        custom_fields = {
            k: v for k, v in row.items()
            if k != "phone"
        }

        lead = Lead(
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            phone=phone,
            custom_fields=custom_fields
        )

        leads_to_insert.append(lead)

    if not leads_to_insert:
        return {"message": "No valid leads found"}

    # 3️⃣ Bulk insert
    db.add_all(leads_to_insert)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Duplicate phone found in database"
        )

    return {
        "message": "Leads uploaded successfully",
        "total_uploaded": len(leads_to_insert)
    }

# ──────────────────────────────────────────────
# ROW 30 – Fetch leads list
# ──────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/leads")
async def list_leads(
    campaign_id: UUID,
    status: LeadStatus | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return a paginated list of leads for a campaign.
    Optionally filter by status.
    """
    await _get_campaign_or_404(campaign_id, current_user.organization_id, db)

    stmt = select(Lead).where(
        Lead.campaign_id == campaign_id,
        Lead.organization_id == current_user.organization_id,
    )

    if status:
        stmt = stmt.where(Lead.status == status)

    stmt = stmt.order_by(Lead.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    leads = result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": len(leads),        # swap for COUNT(*) subquery if dataset is huge
        "leads": [
            {
                "id": str(lead.id),
                "phone": lead.phone,
                "status": lead.status,
                "custom_fields": lead.custom_fields,
                "created_at": lead.created_at.isoformat(),
            }
            for lead in leads
        ],
    }

# ──────────────────────────────────────────────
# ROW 31 – Delete lead
# ──────────────────────────────────────────────

@router.delete("/campaigns/{campaign_id}/leads/{lead_id}", status_code=200)
async def delete_lead(
    campaign_id: UUID,
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Hard-delete a single lead. Use a `deleted_at` soft-delete column instead
    if you need an audit trail."""
    await _get_campaign_or_404(campaign_id, current_user.organization_id, db)

    stmt = (
        delete(Lead)
        .where(
            Lead.id == lead_id,
            Lead.campaign_id == campaign_id,
            Lead.organization_id == current_user.organization_id,
        )
        .returning(Lead.id)
    )

    result = await db.execute(stmt)
    deleted = result.fetchone()

    if not deleted:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.commit()
    return {"message": "Lead removed", "lead_id": str(lead_id)}

# ──────────────────────────────────────────────
# Get Lead Status
# ──────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/leads/{lead_id}/lead-status")
async def get_lead_status(
    campaign_id: UUID,
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the current status of a lead."""
    await _get_campaign_or_404(campaign_id, current_user.organization_id, db)

    stmt = select(Lead).where(
        Lead.id == lead_id,
        Lead.campaign_id == campaign_id,
        Lead.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return {
        "lead_id": str(lead.id),
        "status": lead.status,
    }
