"""
Super Admin panel — only YOU (role=super_admin) can access these.

Endpoints:
  POST   /api/v1/admin/register                         → Create org + admin user
  GET    /api/v1/admin/dashboard                        → Platform-wide stats
  GET    /api/v1/admin/organizations                    → All orgs with stats
  GET    /api/v1/admin/organizations/{id}               → Single org full detail
  PATCH  /api/v1/admin/organizations/{id}               → Update name/status
  DELETE /api/v1/admin/organizations/{id}               → Delete org
  GET    /api/v1/admin/organizations/{id}/users         → Users in org
  GET    /api/v1/admin/organizations/{id}/campaigns     → Campaigns in org
  GET    /api/v1/admin/organizations/{id}/minutes       → Minutes breakdown
  GET    /api/v1/admin/organizations/{id}/wallet        → Wallet + transactions
  POST   /api/v1/admin/organizations/{id}/wallet/credit → Add minutes
  GET    /api/v1/admin/users                            → All users platform-wide
  PATCH  /api/v1/admin/users/{id}/toggle-status         → Activate/deactivate user
"""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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

router = APIRouter(tags=["Super Admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterAdminRequest(BaseModel):
    org_name:        str      = Field(..., min_length=2, max_length=100, examples=["Acme Corp"])
    org_slug:        str      = Field(..., min_length=3, max_length=50,  examples=["acme-corp"])
    first_name:      str      = Field(..., min_length=1, max_length=50)
    last_name:       str      = Field(..., min_length=1, max_length=50)
    email:           EmailStr
    password:        str      = Field(..., min_length=8)
    initial_minutes: int      = Field(default=0, ge=0)
    rate_per_minute: float    = Field(default=0.50, gt=0)

    @field_validator("org_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$", v):
            raise ValueError("Slug: 3-50 chars, lowercase letters, digits, hyphens only.")
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class UpdateOrgRequest(BaseModel):
    name:      Optional[str]  = None
    is_active: Optional[bool] = None


class CreditWalletRequest(BaseModel):
    amount_inr:      float = Field(..., gt=0)
    rate_per_minute: float = Field(..., gt=0)
    description:     str   = Field(default="Manual top-up by Super Admin")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    total_orgs         = await db.scalar(select(func.count()).select_from(Organization))
    active_orgs        = await db.scalar(select(func.count()).select_from(Organization).where(Organization.is_active == True))
    total_admins       = await db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN))
    total_campaigns    = await db.scalar(select(func.count()).select_from(Campaign))
    total_calls        = await db.scalar(select(func.count()).select_from(CallLog))
    total_minutes_used = await db.scalar(select(func.coalesce(func.sum(Wallet.total_minutes_used), 0)).select_from(Wallet)) or 0
    total_amount_paid  = await db.scalar(select(func.coalesce(func.sum(Wallet.total_amount_paid), 0)).select_from(Wallet)) or 0.0
    zero_balance_orgs  = await db.scalar(select(func.count()).select_from(Wallet).where(Wallet.minutes_balance <= 0))

    return {
        "organizations":    {"total": total_orgs, "active": active_orgs, "suspended": total_orgs - active_orgs},
        "users":            {"total_admins": total_admins},
        "calls":            {"total_calls": total_calls, "total_minutes_used": total_minutes_used},
        "revenue":          {"total_amount_paid_inr": round(float(total_amount_paid), 2)},
        "alerts":           {"orgs_with_zero_balance": zero_balance_orgs},
        "campaigns":        {"total": total_campaigns},
    }


# ── Register Org + Admin ──────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register_org_and_admin(
    data: RegisterAdminRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    # ── Step 1: Email must be globally unique ──────────────────────────────
    existing_email = (await db.execute(
        select(User).where(User.email == data.email).limit(1)
    )).scalar_one_or_none()
    if existing_email:
        raise HTTPException(status_code=400, detail=f"Email '{data.email}' is already registered.")

    # ── Step 2: Find existing org OR create new one ────────────────────────
    existing_org = (await db.execute(
        select(Organization).where(Organization.slug == data.org_slug).limit(1)
    )).scalar_one_or_none()

    if existing_org:
        # Case 2 — Org already exists, reuse it
        org = existing_org
        org_is_new = False
        print(f"[REGISTER] 🔗 Joined existing org: '{org.name}' ({org.slug})")
    else:
        # Case 1 — Create new org
        org = Organization(id=uuid.uuid4(), name=data.org_name.strip(), slug=data.org_slug, is_active=True)
        db.add(org)
        await db.flush()
        org_is_new = True
        print(f"[REGISTER] 🆕 New org created: '{org.name}' ({org.slug})")

    # ── Step 3: Create admin user ──────────────────────────────────────────
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

    print(f"[REGISTER]    Admin user: {admin.email} | org_id: {org.id}")

    # ── Step 4: Wallet — only for new orgs ────────────────────────────────
    if org_is_new:
        from app.services.wallet_service import get_or_create_wallet
        wallet = await get_or_create_wallet(str(org.id), db)

        if data.initial_minutes > 0:
            wallet.minutes_balance         = data.initial_minutes
            wallet.rate_per_minute         = data.rate_per_minute
            wallet.total_minutes_purchased = data.initial_minutes
            db.add(WalletTransaction(
                wallet_id=wallet.id,
                transaction_type="credit",
                amount_inr=0.0,
                rate_per_minute=data.rate_per_minute,
                minutes=data.initial_minutes,
                balance_after=data.initial_minutes,
                description="Initial minutes at registration",
            ))

    await db.commit()
    await db.refresh(org)
    await db.refresh(admin)

    return {
        "message": "Admin user created successfully.",
        "organization": {
            "id":      str(org.id),
            "name":    org.name,
            "slug":    org.slug,
            "is_new":  org_is_new,
        },
        "admin_user": {
            "id":         str(admin.id),
            "email":      admin.email,
            "first_name": admin.first_name,
            "last_name":  admin.last_name,
            "role":       admin.role.value,
        },
        "wallet": {
            "minutes_loaded":  data.initial_minutes if org_is_new else "using existing wallet",
            "rate_per_minute": data.rate_per_minute  if org_is_new else "using existing rate",
        },
        "login_credentials": {
            "org_slug": org.slug,
            "email":    admin.email,
            "note":     "Share credentials securely. Admin should change password after first login.",
        },
    }
# ── Organizations ─────────────────────────────────────────────────────────────

@router.get("/organizations")
async def list_organizations(db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    orgs = (await db.execute(select(Organization).order_by(Organization.created_at.desc()))).scalars().all()

    result = []
    for org in orgs:
        user_count     = await db.scalar(select(func.count()).where(User.organization_id == org.id))
        campaign_count = await db.scalar(select(func.count()).where(Campaign.organization_id == org.id))
        wallet         = (await db.execute(select(Wallet).where(Wallet.organization_id == org.id))).scalar_one_or_none()

        result.append({
            "id": str(org.id), "name": org.name, "slug": org.slug,
            "is_active": org.is_active, "created_at": org.created_at,
            "stats":  {"total_users": user_count, "total_campaigns": campaign_count},
            "wallet": {
                "minutes_balance":         wallet.minutes_balance         if wallet else 0,
                "total_minutes_used":      wallet.total_minutes_used      if wallet else 0,
                "total_minutes_purchased": wallet.total_minutes_purchased if wallet else 0,
                "total_amount_paid":       wallet.total_amount_paid       if wallet else 0.0,
                "rate_per_minute":         wallet.rate_per_minute         if wallet else 0.0,
            },
        })
    return result


@router.get("/organizations/{org_id}")
async def get_organization(org_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    users     = (await db.execute(select(User).where(User.organization_id == org_id))).scalars().all()
    campaigns = (await db.execute(select(Campaign).where(Campaign.organization_id == org_id))).scalars().all()
    wallet    = (await db.execute(select(Wallet).where(Wallet.organization_id == org_id))).scalar_one_or_none()

    campaign_ids   = [c.id for c in campaigns]
    total_calls    = await db.scalar(select(func.count(CallLog.id)).where(CallLog.campaign_id.in_(campaign_ids))) if campaign_ids else 0
    total_duration = await db.scalar(select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.campaign_id.in_(campaign_ids))) if campaign_ids else 0

    return {
        "id": str(org.id), "name": org.name, "slug": org.slug,
        "is_active": org.is_active, "created_at": org.created_at,
        "users": [{"id": str(u.id), "email": u.email, "first_name": u.first_name,
                   "last_name": u.last_name, "role": u.role.value, "is_active": u.is_active,
                   "last_login_at": u.last_login_at} for u in users],
        "campaigns": [{"id": str(c.id), "name": c.name,
                       "status": c.status.value if hasattr(c.status, "value") else c.status} for c in campaigns],
        "stats": {"total_users": len(users), "total_campaigns": len(campaigns),
                  "total_calls": total_calls or 0, "total_minutes": round(int(total_duration or 0) / 60, 1)},
        "wallet": {"minutes_balance": wallet.minutes_balance if wallet else 0,
                   "total_minutes_used": wallet.total_minutes_used if wallet else 0,
                   "total_amount_paid": wallet.total_amount_paid if wallet else 0.0,
                   "rate_per_minute": wallet.rate_per_minute if wallet else 0.0},
    }


@router.patch("/organizations/{org_id}")
async def update_organization(org_id: UUID, data: UpdateOrgRequest, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if data.name is not None:
        org.name = data.name.strip()
    if data.is_active is not None:
        org.is_active = data.is_active
    await db.commit()
    await db.refresh(org)
    return {"id": str(org.id), "name": org.name, "is_active": org.is_active}


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await db.delete(org)
    await db.commit()
    return {"message": f"Organization '{org.name}' deleted."}


# ── Per-org: Users ────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/users")
async def org_users(org_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    users = (await db.execute(select(User).where(User.organization_id == org_id))).scalars().all()
    return {
        "org_name": org.name, "total": len(users),
        "users": [{"id": str(u.id), "email": u.email, "first_name": u.first_name,
                   "last_name": u.last_name, "role": u.role.value, "is_active": u.is_active,
                   "created_at": u.created_at, "last_login_at": u.last_login_at} for u in users],
    }


# ── Per-org: Campaigns ────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/campaigns")
async def org_campaigns(org_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    campaigns = (await db.execute(select(Campaign).where(Campaign.organization_id == org_id))).scalars().all()
    result = []
    for c in campaigns:
        call_count   = await db.scalar(select(func.count(CallLog.id)).where(CallLog.campaign_id == c.id))
        duration_sum = await db.scalar(select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.campaign_id == c.id))
        leads_count  = await db.scalar(select(func.count(Lead.id)).where(Lead.campaign_id == c.id))
        result.append({
            "id": str(c.id), "name": c.name,
            "status": c.status.value if hasattr(c.status, "value") else c.status,
            "created_at": c.created_at,
            "stats": {"total_leads": leads_count or 0, "total_calls": call_count or 0,
                      "total_minutes": round(int(duration_sum or 0) / 60, 1)},
        })
    return {"org_name": org.name, "total": len(campaigns), "campaigns": result}


# ── Per-org: Minutes breakdown ────────────────────────────────────────────────

@router.get("/organizations/{org_id}/minutes")
async def org_minutes(org_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    wallet    = (await db.execute(select(Wallet).where(Wallet.organization_id == org_id))).scalar_one_or_none()
    campaigns = (await db.execute(select(Campaign).where(Campaign.organization_id == org_id))).scalars().all()

    breakdown = []
    for c in campaigns:
        duration_sum = await db.scalar(select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.campaign_id == c.id))
        call_count   = await db.scalar(select(func.count(CallLog.id)).where(CallLog.campaign_id == c.id))
        minutes_used = round(int(duration_sum or 0) / 60, 2)
        breakdown.append({
            "campaign_id": str(c.id), "campaign_name": c.name,
            "total_calls": call_count or 0, "duration_sec": int(duration_sum or 0),
            "minutes_used": minutes_used,
            "cost_inr": round(minutes_used * (wallet.rate_per_minute if wallet else 0), 2),
        })

    breakdown.sort(key=lambda x: x["minutes_used"], reverse=True)

    return {
        "org_name": org.name,
        "wallet_summary": {
            "minutes_balance": wallet.minutes_balance if wallet else 0,
            "total_minutes_purchased": wallet.total_minutes_purchased if wallet else 0,
            "total_minutes_used": wallet.total_minutes_used if wallet else 0,
            "total_amount_paid": wallet.total_amount_paid if wallet else 0.0,
            "rate_per_minute": wallet.rate_per_minute if wallet else 0.0,
        },
        "campaign_breakdown": breakdown,
    }


# ── Per-org: Wallet ───────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/wallet")
async def org_wallet(org_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    wallet = (await db.execute(select(Wallet).where(Wallet.organization_id == org_id))).scalar_one_or_none()
    if not wallet:
        return {"org_name": org.name, "wallet": None, "transactions": []}

    txns = (await db.execute(
        select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
    )).scalars().all()

    return {
        "org_name": org.name,
        "wallet": {"id": str(wallet.id), "minutes_balance": wallet.minutes_balance,
                   "rate_per_minute": wallet.rate_per_minute,
                   "total_minutes_purchased": wallet.total_minutes_purchased,
                   "total_minutes_used": wallet.total_minutes_used,
                   "total_amount_paid": wallet.total_amount_paid},
        "total_transactions": len(txns),
        "transactions": [
            {"id": str(tx.id),
             "type": tx.transaction_type.value if hasattr(tx.transaction_type, "value") else tx.transaction_type,
             "minutes": tx.minutes, "amount_inr": tx.amount_inr,
             "balance_after": tx.balance_after, "description": tx.description,
             "created_at": tx.created_at}
            for tx in txns
        ],
    }


@router.post("/organizations/{org_id}/wallet/credit")
async def credit_wallet(org_id: UUID, data: CreditWalletRequest, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    from app.services.wallet_service import credit_wallet as _credit
    result = await _credit(str(org_id), data.amount_inr, data.rate_per_minute, data.description, db)
    await db.commit()
    return {"message": "Wallet credited successfully.", **result}


# ── All users (cross-org) ─────────────────────────────────────────────────────

@router.get("/users")
async def list_all_users(db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    rows = (await db.execute(
        select(User, Organization.name, Organization.slug)
        .join(Organization, User.organization_id == Organization.id)
        .order_by(Organization.name, User.email)
    )).all()

    return {
        "total": len(rows),
        "users": [{"id": str(u.id), "email": u.email, "first_name": u.first_name,
                   "last_name": u.last_name, "role": u.role.value,
                   "organization_name": org_name, "organization_slug": org_slug,
                   "is_active": u.is_active, "last_login_at": u.last_login_at}
                  for u, org_name, org_slug in rows],
    }


@router.patch("/users/{user_id}/toggle-status")
async def toggle_user_status(user_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_super_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    await db.commit()
    return {"id": str(user.id), "email": user.email, "is_active": user.is_active,
            "message": f"User {'activated' if user.is_active else 'deactivated'}."}