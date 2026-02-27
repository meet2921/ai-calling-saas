from pydantic import BaseModel, EmailStr
import uuid

# What browser sends to /register
class RegisterRequest(BaseModel):
    org_name: str
    org_slug: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str

# What browser sends to /login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    org_slug: str

# What browser sends to /refresh
class RefreshRequest(BaseModel):
    refresh_token: str

# What API sends back after login/register
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"