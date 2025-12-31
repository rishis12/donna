from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...integrations import google_integration, microsoft_integration

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/emails")
async def get_emails(
    provider: str = "google",
    max_results: int = 20,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get emails from Gmail or Outlook."""
    emails = []
    
    if provider == "google":
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google not connected")
        emails = await google_integration.list_emails(
            user.google_access_token,
            user.google_refresh_token,
            max_results,
            unread_only
        )
    elif provider == "microsoft":
        if not user.microsoft_access_token:
            raise HTTPException(status_code=400, detail="Microsoft not connected")
        emails = await microsoft_integration.list_emails(
            user.microsoft_access_token,
            max_results,
            unread_only
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {"emails": emails, "count": len(emails)}

@router.get("/emails/count")
async def get_email_count(
    provider: str = "google",
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get count of emails."""
    count = 0
    
    if provider == "google":
        if not user.google_access_token:
            return {"count": 0}
        count = await google_integration.get_email_count(
            user.google_access_token,
            user.google_refresh_token,
            unread_only
        )
    elif provider == "microsoft":
        if not user.microsoft_access_token:
            return {"count": 0}
        count = await microsoft_integration.get_email_count(
            user.microsoft_access_token,
            unread_only
        )
    
    return {"count": count}

@router.get("/teams")
async def get_teams_messages(
    max_results: int = 20,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get messages from Microsoft Teams."""
    if not user.microsoft_access_token:
        raise HTTPException(status_code=400, detail="Microsoft not connected")
    
    messages = await microsoft_integration.list_teams_messages(
        user.microsoft_access_token,
        max_results,
        unread_only
    )
    
    return {"messages": messages, "count": len(messages)}

@router.get("/teams/count")
async def get_teams_message_count(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get count of Teams messages."""
    if not user.microsoft_access_token:
        return {"count": 0}
    
    count = await microsoft_integration.get_teams_message_count(
        user.microsoft_access_token,
        unread_only
    )
    
    return {"count": count}

