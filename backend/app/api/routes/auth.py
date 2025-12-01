from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas import UserCreate, UserLogin, Token, UserResponse
from ...core.database import get_db
from ...core.security import get_password_hash, verify_password, create_access_token
from ...models.user import User
from ...integrations import google_integration, microsoft_integration
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        google_connected=bool(user.google_access_token),
        microsoft_connected=bool(user.microsoft_access_token)
    )

# Google OAuth
@router.get("/google")
async def google_auth():
    return {"auth_url": google_integration.get_auth_url()}

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tokens = await google_integration.exchange_code(code)
    user.google_access_token = tokens["access_token"]
    user.google_refresh_token = tokens.get("refresh_token")
    await db.commit()
    return {"status": "connected"}

# Microsoft OAuth
@router.get("/microsoft")
async def microsoft_auth():
    return {"auth_url": microsoft_integration.get_auth_url()}

@router.get("/microsoft/callback")
async def microsoft_callback(code: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tokens = await microsoft_integration.exchange_code(code)
    user.microsoft_access_token = tokens["access_token"]
    user.microsoft_refresh_token = tokens.get("refresh_token")
    await db.commit()
    return {"status": "connected"}

