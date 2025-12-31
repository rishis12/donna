from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...integrations import google_integration, microsoft_integration
from ...services.llm_service import summarize_communications

router = APIRouter(prefix="/summary", tags=["summary"])

@router.get("/communications")
async def get_communications_summary(
    include_emails: bool = True,
    include_teams: bool = True,
    max_emails: int = 10,
    max_teams: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get a summary of all communications (emails and Teams messages).
    Uses LLM to create an intelligent summary like a real assistant would.
    """
    emails = []
    teams_messages = []
    
    # Fetch Gmail emails
    if include_emails and user.google_access_token:
        try:
            gmail_emails = await google_integration.list_emails(
                user.google_access_token,
                user.google_refresh_token,
                max_emails,
                unread_only=True
            )
            emails.extend([{**e, "provider": "gmail"} for e in gmail_emails])
        except Exception as e:
            print(f"Failed to fetch Gmail: {e}")
    
    # Fetch Outlook emails
    if include_emails and user.microsoft_access_token:
        try:
            outlook_emails = await microsoft_integration.list_emails(
                user.microsoft_access_token,
                max_emails,
                unread_only=True
            )
            emails.extend([{**e, "provider": "outlook"} for e in outlook_emails])
        except Exception as e:
            print(f"Failed to fetch Outlook: {e}")
    
    # Fetch Teams messages
    if include_teams and user.microsoft_access_token:
        try:
            teams_messages = await microsoft_integration.list_teams_messages(
                user.microsoft_access_token,
                max_teams,
                unread_only=True
            )
        except Exception as e:
            print(f"Failed to fetch Teams: {e}")
    
    # Use LLM to create a summary
    summary = await summarize_communications(emails, teams_messages)
    
    return {
        "summary": summary,
        "emailCount": len(emails),
        "teamsCount": len(teams_messages),
        "emails": emails[:5],  # Return first 5 for preview
        "teamsMessages": teams_messages[:5]  # Return first 5 for preview
    }

