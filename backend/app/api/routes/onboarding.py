from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas import OnboardingStatusResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: User = Depends(get_current_user)
):
    """Get onboarding completion status for the current user."""
    return OnboardingStatusResponse(
        onboarding_complete=user.onboarding_complete or False
    )

@router.post("/complete")
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark onboarding as complete for the current user."""
    user.onboarding_complete = True
    await db.commit()
    return {"status": "completed", "onboarding_complete": True}
