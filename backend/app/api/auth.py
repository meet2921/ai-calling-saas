from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.email == user_data.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_data.email,
        password=hash_password(user_data.password),
        organization_id=user_data.organization_id
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"message": "User created successfully"}

@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.email == user_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})

    return {"access_token": token, "token_type": "bearer"}
