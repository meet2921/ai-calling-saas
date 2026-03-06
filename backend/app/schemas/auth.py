"""
app/schemas/auth.py

ORIGINAL schemas (unchanged):
    RegisterRequest, LoginRequest, RefreshRequest, TokenResponse

NEW schemas added:
    ForgotPasswordRequest   ← POST /forgot-password
    ResetPasswordRequest    ← POST /reset-password
    MsgResponse             ← generic {"message": "..."} response
"""
import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import uuid

_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$")

def _validate_password(v: str) -> str:
    if not _PASSWORD_RE.match(v):
        raise ValueError(
            "Password must be at least 8 characters and include "
            "uppercase, lowercase, a digit, and a special character."
        )
    return v


# What browser sends to /register
class RegisterRequest(BaseModel):
    org_name:   str      = Field(..., min_length=2, max_length=100)
    org_slug:   str      = Field(..., min_length=3, max_length=50)
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
        if not re.match(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$", v):
            raise ValueError(
                "Slug must be 3-50 chars: lowercase letters, numbers, hyphens. "
                "Cannot start or end with a hyphen."
            )
        return v
    

# What browser sends to /login
class LoginRequest(BaseModel):
    org_slug: str
    email:    EmailStr
    password: str

    @field_validator("org_slug")
    @classmethod
    def normalise_slug(cls, v: str) -> str:
        return v.strip().lower()
    
# What browser sends to /refresh
class RefreshRequest(BaseModel):
    refresh_token: str

# What API sends back after login/register
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"



# ─── NEW ──────────────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    """
    Public endpoint — user provides their registered email + org slug.
    Always returns 200 to prevent user enumeration.
    """
    email:    EmailStr
    org_slug: str

    @field_validator("org_slug")
    @classmethod
    def normalise_slug(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    """
    Public endpoint — user arrives here from the email reset link.
    `reset_token` is the opaque token from the email URL (not a JWT).
    """
    reset_token:  str = Field(..., min_length=10)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)


class MsgResponse(BaseModel):
    """Generic {"message": "..."} response for logout, forgot, reset."""
    message: str

class UserProfile(BaseModel):
    id:              str
    email:           str
    first_name:      str
    last_name:       str
    role:            str
    organization_id: str

    model_config = {"from_attributes": True}