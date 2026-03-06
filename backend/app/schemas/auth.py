import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole

_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$")


def _validate_password(v: str) -> str:
    if not _PASSWORD_RE.match(v):
        raise ValueError(
            "Password needs 8+ chars with uppercase, lowercase, digit, special character."
        )
    return v


# ─── REGISTER (find-or-create org) ────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """
    Single registration schema.

    Logic in backend:
      1. Look up org_slug in organizations table
      2. If EXISTS  → use existing org_id, create user with role='agent'
      3. If MISSING → create new org, create user with role='admin'
    """
    
    org_name:   str      = Field(..., min_length=2, max_length=100, examples=["ABC Corp"])
    org_slug:   str      = Field(..., min_length=2, max_length=50,  examples=["abc-xyz"])
    first_name: str      = Field(..., min_length=1, max_length=50)
    last_name:  str      = Field(..., min_length=1, max_length=50)
    email:      EmailStr
    password:   str

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("org_slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]{1}$", v):
            raise ValueError("Slug: lowercase letters, numbers, hyphens only. e.g. abc-xyz")
        return v


# ─── LOGIN ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Login with org_slug + email + password.
    org_slug scopes the user to their organization.
    """
    org_slug: str      = Field(..., examples=["abc-xyz"])
    email:    EmailStr = Field(..., examples=["admin@abc.com"])
    password: str      = Field(..., examples=["Secure@123"])

    @field_validator("org_slug")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().lower()


# ─── TOKEN REFRESH ────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


# ─── FORGOT / RESET PASSWORD ──────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email:    EmailStr = Field(..., examples=["admin@abc.com"])
    org_slug: str      = Field(..., examples=["abc-xyz"])

    @field_validator("org_slug")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    """
    After calling /forgot-password:
      1. Check uvicorn terminal for: [RESET] Token → xxxxxxxx
      2. Send that value here as reset_token

    Body:
      {
        "reset_token":  "xxxxxxxx",
        "new_password": "NewPass1!"
      }
    """
    reset_token:  str = Field(..., min_length=5, examples=["token_from_email_or_terminal"])
    new_password: str = Field(..., examples=["NewSecurePass1!"])

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)


# ─── RESPONSES ────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class MsgResponse(BaseModel):
    message: str


class UserProfile(BaseModel):
    id:              str
    email:           str
    first_name:      str
    last_name:       str
    role:            UserRole
    organization_id: str
    org_name:        str
    org_slug:        str

    model_config = {"from_attributes": True}


class OrgCheckResponse(BaseModel):
    """Returned by GET /auth/org/{slug} so frontend knows if org exists."""
    exists:   bool
    org_name: str  = ""
    org_slug: str  = ""
    message:  str  = ""
