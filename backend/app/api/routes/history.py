from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from ..schemas import HistoryEntryCreate, HistoryEntryResponse, HistoryListResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...models.user_history import UserHistory

router = APIRouter(prefix="/history", tags=["history"])

@router.get("", response_model=HistoryListResponse)
async def get_history(
    limit: Optional[int] = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's interaction history."""
    result = await db.execute(
        select(UserHistory)
        .where(UserHistory.user_id == user.id)
        .order_by(desc(UserHistory.timestamp))
        .limit(limit or 100)
    )
    entries = result.scalars().all()
    
    return HistoryListResponse(
        entries=[
            HistoryEntryResponse(
                id=entry.id,
                message=entry.message,
                intent=entry.intent,
                metadata=entry.meta_data,
                timestamp=entry.timestamp
            )
            for entry in entries
        ]
    )

@router.post("", response_model=HistoryEntryResponse)
async def create_history_entry(
    data: HistoryEntryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new history entry for the user."""
    entry = UserHistory(
        user_id=user.id,
        message=data.message,
        intent=data.intent,
        meta_data=data.metadata
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    return HistoryEntryResponse(
        id=entry.id,
        message=entry.message,
        intent=entry.intent,
        metadata=entry.meta_data,
        timestamp=entry.timestamp
    )
