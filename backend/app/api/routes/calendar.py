from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas import EventCreate, EventUpdate
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...integrations import google_integration, microsoft_integration

router = APIRouter(prefix="/calendar", tags=["calendar"])

@router.get("/events")
async def list_events(
    provider: str = "google",
    max_results: int = 10,
    user: User = Depends(get_current_user)
):
    if provider == "google":
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google not connected")
        events = await google_integration.list_events(
            user.google_access_token,
            user.google_refresh_token,
            max_results
        )
    elif provider == "microsoft":
        if not user.microsoft_access_token:
            raise HTTPException(status_code=400, detail="Microsoft not connected")
        events = await microsoft_integration.list_events(
            user.microsoft_access_token,
            max_results
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {"events": events}

@router.post("/create")
async def create_event(
    data: EventCreate,
    provider: str = "google",
    user: User = Depends(get_current_user)
):
    if provider == "google":
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google not connected")
        event = await google_integration.create_event(
            user.google_access_token,
            user.google_refresh_token,
            data.summary,
            data.start_time,
            data.end_time,
            data.attendees,
            data.description
        )
    elif provider == "microsoft":
        if not user.microsoft_access_token:
            raise HTTPException(status_code=400, detail="Microsoft not connected")
        event = await microsoft_integration.create_event(
            user.microsoft_access_token,
            data.summary,
            data.start_time,
            data.end_time,
            data.attendees,
            data.description
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {"event": event}

@router.patch("/update/{event_id}")
async def update_event(
    event_id: str,
    data: EventUpdate,
    provider: str = "google",
    user: User = Depends(get_current_user)
):
    updates = data.model_dump(exclude_none=True)
    
    if provider == "google":
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google not connected")
        
        google_updates = {}
        if "summary" in updates:
            google_updates["summary"] = updates["summary"]
        if "start_time" in updates:
            google_updates["start"] = {"dateTime": updates["start_time"].isoformat(), "timeZone": "UTC"}
        if "end_time" in updates:
            google_updates["end"] = {"dateTime": updates["end_time"].isoformat(), "timeZone": "UTC"}
        if "description" in updates:
            google_updates["description"] = updates["description"]
        
        event = await google_integration.update_event(
            user.google_access_token,
            user.google_refresh_token,
            event_id,
            google_updates
        )
    elif provider == "microsoft":
        if not user.microsoft_access_token:
            raise HTTPException(status_code=400, detail="Microsoft not connected")
        
        ms_updates = {}
        if "summary" in updates:
            ms_updates["subject"] = updates["summary"]
        if "start_time" in updates:
            ms_updates["start"] = {"dateTime": updates["start_time"].isoformat(), "timeZone": "UTC"}
        if "end_time" in updates:
            ms_updates["end"] = {"dateTime": updates["end_time"].isoformat(), "timeZone": "UTC"}
        if "description" in updates:
            ms_updates["body"] = {"contentType": "text", "content": updates["description"]}
        
        event = await microsoft_integration.update_event(
            user.microsoft_access_token,
            event_id,
            ms_updates
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {"event": event}

