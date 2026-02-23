from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    organization_id: Optional[UUID] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
