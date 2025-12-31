from fastapi import APIRouter, Depends, HTTPException
from ..schemas import EmailDraft, EmailSend
from ..deps import get_current_user
from ...models.user import User
from ...integrations import google_integration, microsoft_integration
from ...services.llm_service import draft_email_content

router = APIRouter(prefix="/email", tags=["email"])

@router.post("/draft")
async def draft_email(
    data: EmailDraft,
    user: User = Depends(get_current_user)
):
    # Use LLM to improve the draft if body seems like a prompt
    if len(data.body) < 100 and not data.body.startswith("Dear"):
        result = await draft_email_content(data.to, data.subject, data.body)
        return {
            "draft": {
                "to": data.to,
                "subject": result.get("subject", data.subject),
                "body": result.get("body", data.body)
            }
        }
    
    return {"draft": {"to": data.to, "subject": data.subject, "body": data.body}}

@router.post("/send")
async def send_email(
    data: EmailSend,
    user: User = Depends(get_current_user)
):
    if data.provider == "google":
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google not connected")
        result = await google_integration.send_email(
            user.google_access_token,
            user.google_refresh_token,
            data.to,
            data.subject,
            data.body
        )
    elif data.provider == "microsoft":
        if not user.microsoft_access_token:
            raise HTTPException(status_code=400, detail="Microsoft not connected")
        result = await microsoft_integration.send_email(
            user.microsoft_access_token,
            data.to,
            data.subject,
            data.body
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {"status": "sent", "result": result}

@router.post("/mark-read")
async def mark_emails_read(
    data: dict,  # {"email_ids": ["id1", "id2"] or "all": true}
    user: User = Depends(get_current_user)
):
    if not user.google_access_token:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    email_ids = data.get("email_ids", [])
    mark_all = data.get("all", False)
    
    result = await google_integration.mark_emails_as_read(
        user.google_access_token,
        user.google_refresh_token,
        email_ids if not mark_all else None,
        mark_all=mark_all
    )
    
    return result

