"""
app/api/v1/admin.py

Super Admin panel — ONLY YOU can access these endpoints (role = super_admin).

Capabilities:
  POST   /admin/register                          → Create org + admin user
  GET    /admin/dashboard                         → Global platform stats
  GET    /admin/organizations                     → All orgs with stats
  GET    /admin/organizations/{id}                → Single org detail
  PATCH  /admin/organizations/{id}                → Update org name / status
  DELETE /admin/organizations/{id}                → Delete org (cascades)
  GET    /admin/organizations/{id}/users          → All users in org
  GET    /admin/organizations/{id}/campaigns      → All campaigns in org
  GET    /admin/organizations/{id}/minutes        → Minutes used per user
  GET    /admin/organizations/{id}/wallet         → Wallet + transactions
  POST   /admin/organizations/{id}/wallet/credit  → Top up minutes
  GET    /admin/users                             → All admin users across platform
  PATCH  /admin/users/{id}/toggle-status          → Activate / deactivate user
"""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID

from app.db.session import get_db
from app.core.deps import require_super_admin
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.campaigns import Campaign
from app.models.call_logs import CallLog
from app.models.lead import Lead
from app.models.wallet import Wallet, WalletTransaction

router = APIRouter(prefix="/api/v1/admin", tags=["Super Admin"])


# ── Request / Response schemas ────────────────────────────────────────────────

class RegisterAdminRequest(BaseModel):
    """
    Super Admin calls this to onboard a new customer.
    Creates:  1 Organization  +  1 Admin User  +  (optionally) pre-loads minutes.
    The admin then logs in with:  org_slug + email + password.
    """
    # Organization
    org_name: str = Field(..., min_length=2, max_length=100, examples=["Acme Corp"])
    org_slug: str = Field(..., min_length=3, max_length=50,  examples=["acme-corp"],
                          description="Unique login slug — lowercase, hyphens only")

    # Admin user
    first_name: str      = Field(..., min_length=1, max_length=50)
    last_name:  str      = Field(..., min_length=1, max_length=50)
    email:      EmailStr
    password:   str      = Field(..., min_length=8, description="Temporary password — admin should change after first login")

    # Optional wallet seed
    initial_minutes: int   = Field(default=0, ge=0, description="Minutes to pre-load (0 = none)")
    rate_per_minute: float = Field(default=0.50, gt=0, description="₹ per minute calling rate")

    @field_validator("org_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$", v):
            raise ValueError("Slug: 3–50 chars, lowercase letters, digits, hyphens. Cannot start/end with hyphen.")
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class UpdateOrgRequest(BaseModel):
    name:      Optional[str]  = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None


class CreditWalletRequest(BaseModel):
    amount_inr:      float = Field(..., gt=0, description="Amount in ₹")
    rate_per_minute: float = Field(..., gt=0, description="₹ per minute")
    description:     str   = Field(default="Manual top-up by Super Admin")


class SetMinutesRequest(BaseModel):
    minutes:         int   = Field(..., ge=0, description="Set wallet balance to this many minutes")
    rate_per_minute: float = Field(..., gt=0, description="₹ per minute")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", summary="Global platform stats")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Top-level numbers for your Super Admin dashboard."""
    total_orgs        = await db.scalar(select(func.count()).select_from(Organization))
    active_orgs       = await db.scalar(select(func.count()).select_from(Organization).where(Organization.is_active == True))
    total_admins      = await db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN))
    total_campaigns   = await db.scalar(select(func.count()).select_from(Campaign))
    total_calls       = await db.scalar(select(func.count()).select_from(CallLog))

    # Total minutes used across all orgs
    total_minutes_used = await db.scalar(
        select(func.coalesce(func.sum(Wallet.total_minutes_used), 0)).select_from(Wallet)
    ) or 0

    # Total revenue (amount paid)
    total_amount_paid = await db.scalar(
        select(func.coalesce(func.sum(Wallet.total_amount_paid), 0)).select_from(Wallet)
    ) or 0.0

    # Orgs with zero balance (need recharge)
    low_balance_orgs = await db.scalar(
        select(func.count()).select_from(Wallet).where(Wallet.minutes_balance <= 0)
    )

    return {
        "organizations": {
            "total":  total_orgs,
            "active": active_orgs,
            "suspended": total_orgs - active_orgs,
        },
        "users": {
            "total_admins": total_admins,
        },
        "calls": {
            "total_calls":        total_calls,
            "total_minutes_used": total_minutes_used,
        },
        "revenue": {
            "total_amount_paid_inr": round(float(total_amount_paid), 2),
        },
        "alerts": {
            "orgs_with_zero_balance": low_balance_orgs,
        },
        "campaigns": {
            "total": total_campaigns,
        },
    }


# ── Register Org + Admin ──────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED,
             summary="Onboard a new customer — creates org + admin user")
async def register_org_and_admin(
    data: RegisterAdminRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    This is the ONLY way to create an organization and its admin.
    Public /register has been removed — only Super Admin onboards customers.

    After calling this, share with the admin:
      - Login URL: /login
      - org_slug, email, password (they should change password after first login)
    """
    # 1. Check slug not taken
    existing = await db.execute(select(Organization).where(Organization.slug == data.org_slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Slug '{data.org_slug}' is already taken.")

    # 2. Check email not already registered
    existing_email = await db.execute(select(User).where(User.email == data.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Email '{data.email}' is already registered.")

    # 3. Create organization
    org = Organization(
        id=uuid.uuid4(),
        name=data.org_name.strip(),
        slug=data.org_slug,
        is_active=True,
    )
    db.add(org)
    await db.flush()  # get org.id before commit

    # 4. Create admin user for this org
    admin = User(
        id=uuid.uuid4(),
        organization_id=org.id,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.ADMIN,
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        is_active=True,
    )
    db.add(admin)
    await db.flush()

    # 5. Create wallet
    from app.services.wallet_service import get_or_create_wallet
    wallet = await get_or_create_wallet(str(org.id), db)

    # 6. Pre-load minutes if specified
    if data.initial_minutes > 0:
        wallet.minutes_balance         = data.initial_minutes
        wallet.rate_per_minute         = data.rate_per_minute
        wallet.total_minutes_purchased = data.initial_minutes

        # Log the credit transaction
        tx = WalletTransaction(
            wallet_id=wallet.id,
            transaction_type="credit",
            amount_inr=0.0,
            rate_per_minute=data.rate_per_minute,
            minutes=data.initial_minutes,
            balance_after=data.initial_minutes,
            description="Initial minutes loaded at registration",
        )
        db.add(tx)

    await db.commit()
    await db.refresh(org)
    await db.refresh(admin)

    print(f"[ADMIN] ✅ New org registered: '{org.name}' ({org.slug}) | Admin: {admin.email}")

    return {
        "message": "Organization and admin created successfully.",
        "organization": {
            "id":         str(org.id),
            "name":       org.name,
            "slug":       org.slug,
            "is_active":  org.is_active,
            "created_at": org.created_at,
        },
        "admin_user": {
            "id":         str(admin.id),
            "email":      admin.email,
            "first_name": admin.first_name,
            "last_name":  admin.last_name,
            "role":       admin.role.value,
        },
        "wallet": {
            "minutes_loaded": data.initial_minutes,
            "rate_per_minute": data.rate_per_minute,
        },
        "login_credentials": {
            "org_slug": org.slug,
            "email":    admin.email,
            "password": "*** (as set) — share securely with admin ***",
            "note":     "Admin should change password after first login.",
        },
    }


# ── Organizations ─────────────────────────────────────────────────────────────

@router.get("/organizations", summary="List all organizations with stats")
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    result = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
    orgs   = result.scalars().all()

    response = []
    for org in orgs:
        user_count     = await db.scalar(select(func.count()).where(User.organization_id == org.id))
        campaign_count = await db.scalar(select(func.count()).where(Campaign.organization_id == org.id))
        call_count     = await db.scalar(select(func.count(CallLog.id)).where(CallLog.campaign_id.in_(
            select(Campaign.id).where(Campaign.organization_id == org.id)
        )))

        # Wallet info
        wallet = (await db.execute(select(Wallet).where(Wallet.organization_id == org.id))).scalar_one_or_none()

        response.append({
            "id":               str(org.id),
            "name":             org.name,
            "slug":             org.slug,
            "is_active":        org.is_active,
            "created_at":       org.created_at,
            "stats": {
                "total_users":     user_count,
                "total_campaigns": campaign_count,
                "total_calls":     call_count or 0,
            },
            "wallet": {
                "minutes_balance":        wallet.minutes_balance        if wallet else 0,
                "total_minutes_used":     wallet.total_minutes_used     if wallet else 0,
                "total_minutes_purchased":wallet.total_minutes_purchased if wallet else 0,
                "total_amount_paid":      wallet.total_amount_paid      if wallet else 0.0,
                "rate_per_minute":        wallet.rate_per_minute        if wallet else 0.0,
            },
        })

    return response


@router.get("/organizations/{org_id}", summary="Full detail for one organization")
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Users
    users_result = await db.execute(select(User).where(User.organization_id == org_id))
    users = users_result.scalars().all()

    # Campaigns
    campaigns_result = await db.execute(select(Campaign).where(Campaign.organization_id == org_id))
    campaigns = campaigns_result.scalars().all()
    campaign_ids = [c.id for c in campaigns]

    # Total calls & minutes
    total_calls = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.campaign_id.in_(campaign_ids))
    ) if campaign_ids else 0

    total_duration = await db.scalar(
        select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.campaign_id.in_(campaign_ids))
    ) if campaign_ids else 0

    # Wallet
    wallet = (await db.execute(select(Wallet).where(Wallet.organization_id == org_id))).scalar_one_or_none()

    return {
        "id":         str(org.id),
        "name":       org.name,
        "slug":       org.slug,
        "is_active":  org.is_active,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
        "users": [
            {
                "id":         str(u.id),
                "email":      u.email,
                "first_name": u.first_name,
                "last_name":  u.last_name,
                "role":       u.role.value,
                "is_active":  u.is_active,
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
            }
            for u in users
        ],
        "campaigns": [
            {
                "id":     str(c.id),
                "name":   c.name,
                "status": c.status.value if hasattr(c.status, "value") else c.status,
                "created_at": c.created_at,
            }
            for c in campaigns
        ],
        "stats": {
            "total_users":        len(users),
            "total_campaigns":    len(campaigns),
            "total_calls":        total_calls or 0,
            "total_duration_sec": int(total_duration or 0),
            "total_duration_min": round(int(total_duration or 0) / 60, 1),
        },
        "wallet": {
            "minutes_balance":         wallet.minutes_balance         if wallet else 0,
            "rate_per_minute":         wallet.rate_per_minute         if wallet else 0.0,
            "total_minutes_purchased": wallet.total_minutes_purchased if wallet else 0,
            "total_minutes_used":      wallet.total_minutes_used      if wallet else 0,
            "total_amount_paid":       wallet.total_amount_paid       if wallet else 0.0,
        },
    }


@router.patch("/organizations/{org_id}", summary="Update org name or active status")
async def update_organization(
    org_id: UUID,
    data: UpdateOrgRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if data.name is not None:
        org.name = data.name.strip()
    if data.is_active is not None:
        org.is_active = data.is_active

    await db.commit()
    await db.refresh(org)
    return {"id": str(org.id), "name": org.name, "is_active": org.is_active,
            "message": f"Organization {'activated' if org.is_active else 'suspended'}."}


@router.delete("/organizations/{org_id}", summary="Delete organization (cascades to all data)")
async def delete_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.delete(org)
    await db.commit()
    return {"message": f"Organization '{org.name}' deleted permanently."}


# ── Per-Org: Users ────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/users", summary="All users in an organization")
async def org_users(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    result = await db.execute(select(User).where(User.organization_id == org_id))
    users  = result.scalars().all()

    return {
        "org_name":   org.name,
        "org_slug":   org.slug,
        "total":      len(users),
        "users": [
            {
                "id":           str(u.id),
                "email":        u.email,
                "first_name":   u.first_name,
                "last_name":    u.last_name,
                "role":         u.role.value,
                "is_active":    u.is_active,
                "created_at":   u.created_at,
                "last_login_at":u.last_login_at,
            }
            for u in users
        ],
    }


# ── Per-Org: Campaigns ────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/campaigns", summary="All campaigns in an organization")
async def org_campaigns(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    result    = await db.execute(select(Campaign).where(Campaign.organization_id == org_id))
    campaigns = result.scalars().all()

    campaign_data = []
    for c in campaigns:
        call_count = await db.scalar(
            select(func.count(CallLog.id)).where(CallLog.campaign_id == c.id)
        )
        duration_sum = await db.scalar(
            select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.campaign_id == c.id)
        )
        leads_count = await db.scalar(
            select(func.count(Lead.id)).where(Lead.campaign_id == c.id)
        )
        campaign_data.append({
            "id":           str(c.id),
            "name":         c.name,
            "status":       c.status.value if hasattr(c.status, "value") else c.status,
            "created_at":   c.created_at,
            "stats": {
                "total_leads":      leads_count or 0,
                "total_calls":      call_count or 0,
                "total_minutes":    round(int(duration_sum or 0) / 60, 1),
            },
        })

    return {
        "org_name":  org.name,
        "total":     len(campaigns),
        "campaigns": campaign_data,
    }


# ── Per-Org: Minutes breakdown ────────────────────────────────────────────────

@router.get("/organizations/{org_id}/minutes", summary="Minutes used — breakdown by campaign")
async def org_minutes_breakdown(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Shows how many calling minutes each campaign has consumed in this org.
    Also shows the wallet summary at the top.
    """
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    wallet = (await db.execute(select(Wallet).where(Wallet.organization_id == org_id))).scalar_one_or_none()

    # Per-campaign breakdown
    campaigns_result = await db.execute(select(Campaign).where(Campaign.organization_id == org_id))
    campaigns = campaigns_result.scalars().all()

    breakdown = []
    for c in campaigns:
        duration_sum = await db.scalar(
            select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.campaign_id == c.id)
        )
        call_count = await db.scalar(
            select(func.count(CallLog.id)).where(CallLog.campaign_id == c.id)
        )
        minutes_used = round(int(duration_sum or 0) / 60, 2)
        breakdown.append({
            "campaign_id":   str(c.id),
            "campaign_name": c.name,
            "total_calls":   call_count or 0,
            "duration_sec":  int(duration_sum or 0),
            "minutes_used":  minutes_used,
            "cost_inr":      round(minutes_used * (wallet.rate_per_minute if wallet else 0), 2),
        })

    breakdown.sort(key=lambda x: x["minutes_used"], reverse=True)

    return {
        "org_name": org.name,
        "wallet_summary": {
            "minutes_balance":         wallet.minutes_balance         if wallet else 0,
            "total_minutes_purchased": wallet.total_minutes_purchased if wallet else 0,
            "total_minutes_used":      wallet.total_minutes_used      if wallet else 0,
            "total_amount_paid":       wallet.total_amount_paid       if wallet else 0.0,
            "rate_per_minute":         wallet.rate_per_minute         if wallet else 0.0,
        },
        "campaign_breakdown": breakdown,
    }


# ── Wallet management ─────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/wallet", summary="Wallet balance + transaction history")
async def org_wallet(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    wallet = (await db.execute(select(Wallet).where(Wallet.organization_id == org_id))).scalar_one_or_none()
    if not wallet:
        return {"org_name": org.name, "wallet": None, "transactions": []}

    tx_result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
    )
    transactions = tx_result.scalars().all()

    return {
        "org_name": org.name,
        "wallet": {
            "id":                      str(wallet.id),
            "minutes_balance":         wallet.minutes_balance,
            "rate_per_minute":         wallet.rate_per_minute,
            "total_minutes_purchased": wallet.total_minutes_purchased,
            "total_minutes_used":      wallet.total_minutes_used,
            "total_amount_paid":       wallet.total_amount_paid,
            "updated_at":              wallet.updated_at,
        },
        "total_transactions": len(transactions),
        "transactions": [
            {
                "id":              str(tx.id),
                "type":            tx.transaction_type.value if hasattr(tx.transaction_type, "value") else tx.transaction_type,
                "minutes":         tx.minutes,
                "amount_inr":      tx.amount_inr,
                "rate_per_minute": tx.rate_per_minute,
                "balance_after":   tx.balance_after,
                "description":     tx.description,
                "created_at":      tx.created_at,
            }
            for tx in transactions
        ],
    }


@router.post("/organizations/{org_id}/wallet/credit", summary="Credit minutes to org wallet")
async def credit_wallet(
    org_id: UUID,
    data: CreditWalletRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Tops up an organization's minute balance."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    from app.services.wallet_service import credit_wallet as _credit
    result = await _credit(
        organization_id=str(org_id),
        amount_inr=data.amount_inr,
        rate_per_minute=data.rate_per_minute,
        description=data.description,
        db=db,
    )
    await db.commit()
    return {"message": "Wallet credited successfully.", **result}


@router.post("/organizations/{org_id}/wallet/set-minutes", summary="Directly set wallet balance")
async def set_wallet_minutes(
    org_id: UUID,
    data: SetMinutesRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Override wallet balance directly — useful for corrections."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    from app.services.wallet_service import get_or_create_wallet
    wallet = await get_or_create_wallet(str(org_id), db)

    old_balance             = wallet.minutes_balance
    wallet.minutes_balance  = data.minutes
    wallet.rate_per_minute  = data.rate_per_minute

    tx = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type="credit",
        amount_inr=0.0,
        rate_per_minute=data.rate_per_minute,
        minutes=data.minutes,
        balance_after=data.minutes,
        description=f"Manual balance override by Super Admin (was {old_balance} min)",
    )
    db.add(tx)
    await db.commit()

    return {
        "message": f"Balance set to {data.minutes} minutes.",
        "old_balance": old_balance,
        "new_balance": data.minutes,
    }


# ── All Users (cross-org) ─────────────────────────────────────────────────────

@router.get("/users", summary="All admin users across all organizations")
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    result = await db.execute(
        select(User, Organization.name, Organization.slug)
        .join(Organization, User.organization_id == Organization.id)
        .order_by(Organization.name, User.email)
    )
    rows = result.all()

    return {
        "total": len(rows),
        "users": [
            {
                "id":                str(u.id),
                "email":             u.email,
                "first_name":        u.first_name,
                "last_name":         u.last_name,
                "role":              u.role.value,
                "organization_id":   str(u.organization_id),
                "organization_name": org_name,
                "organization_slug": org_slug,
                "is_active":         u.is_active,
                "created_at":        u.created_at,
                "last_login_at":     u.last_login_at,
            }
            for u, org_name, org_slug in rows
        ],
    }


@router.patch("/users/{user_id}/toggle-status", summary="Activate or deactivate a user")
async def toggle_user_status(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    return {
        "id":        str(user.id),
        "email":     user.email,
        "is_active": user.is_active,
        "message":   f"User {'activated' if user.is_active else 'deactivated'} successfully.",
    }
