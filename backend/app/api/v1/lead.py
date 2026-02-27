from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import csv
import io

from app.db.session import get_db
from app.models.lead import Lead
from app.models.campaigns import Campaign
from app.core.deps import get_current_user

router = APIRouter()

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