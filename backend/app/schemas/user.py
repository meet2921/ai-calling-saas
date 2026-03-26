from pydantic import BaseModel, EmailStr


class UserProfileUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None