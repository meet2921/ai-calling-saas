from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
import uuid

from app.db.session import get_db
from app.core.deps import require_owner
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.campaigns import Campaign

router = APIRouter(prefix="/admin", tags=["Super Admin"])

@router.get("/organizations")
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    result = await db.execute(select(Organization))
    organizations = result.scalars().all()

    response = []

    for org in organizations:
        user_count = await db.scalar(
            select(func.count()).where(User.organization_id == org.id)
        )

        campaign_count = await db.scalar(
            select(func.count()).where(Campaign.organization_id == org.id)
        )

        response.append({
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "is_active": org.is_active,
            "total_users": user_count,
            "total_campaigns": campaign_count,
            "created_at": org.created_at
        })

    return response

@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    org = await db.get(Organization, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_count = await db.scalar(
        select(func.count()).where(User.organization_id == org.id)
    )

    campaign_count = await db.scalar(
        select(func.count()).where(Campaign.organization_id == org.id)
    )

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "is_active": org.is_active,
        "total_users": user_count,
        "total_campaigns": campaign_count,
        "created_at": org.created_at
    }

@router.post("/organizations")
async def create_organization(
    name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    slug = name.lower().replace(" ", "-")

    org = Organization(
        id=uuid.uuid4(),
        name=name,
        slug=slug,
    )

    db.add(org)
    await db.commit()
    await db.refresh(org)

    return org


@router.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    org = await db.get(Organization, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.delete(org)
    await db.commit()

    return {"message": "Organization deleted"}

@router.patch("/organizations/{org_id}/toggle-status")
async def toggle_organization_status(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    org = await db.get(Organization, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = not org.is_active

    await db.commit()
    await db.refresh(org)

    return {
        "id": org.id,
        "is_active": org.is_active
    }


@router.get("/users")
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    result = await db.execute(
        select(User, Organization.name)
        .join(Organization, User.organization_id == Organization.id)
    )

    rows = result.all()

    response = []
    for user, org_name in rows:
        response.append({
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "organization_name": org_name,
            "is_active": user.is_active,
            "created_at": user.created_at
        })

    return response 

@router.patch("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "is_active": user.is_active
    }


#add global dashboard analytics

@router.get("/dashboard")
async def owner_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner)
):
    total_orgs = await db.scalar(select(func.count()).select_from(Organization))
    total_users = await db.scalar(select(func.count()).select_from(User))
    total_campaigns = await db.scalar(select(func.count()).select_from(Campaign))
    

    return {
        "total_organizations": total_orgs,
        "total_users": total_users,
        "total_campaigns": total_campaigns
    }