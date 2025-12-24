from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from ..schemas import UtteranceRequest, IntentResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...models.interaction import Interaction
from ...models.reminder import Reminder, ReminderStatus
from ...services.llm_service import parse_utterance, transcribe_audio
from ...integrations import google_integration
from .action import store_pending_action
import uuid
from datetime import datetime

router = APIRouter(prefix="/utterance", tags=["utterance"])

async def get_user_reminders_text(db: AsyncSession, user_id: str) -> str:
    """Fetch user's active reminders and format as text."""
    result = await db.execute(
        select(Reminder)
        .where(Reminder.user_id == user_id)
        .where(Reminder.status == ReminderStatus.ACTIVE)
        .order_by(Reminder.due_time)
    )
    reminders = result.scalars().all()
    
    if not reminders:
        return "You have no active reminders."
    
    lines = ["Here are your active reminders:"]
    for r in reminders:
        time_str = r.due_time.strftime('%B %d at %I:%M %p')
        lines.append(f"  • {r.text} — {time_str}")
    
    return "\n".join(lines)


async def get_user_calendar_context(user: User) -> str:
    """Fetch user's upcoming events and format them for the LLM."""
    if not user.google_access_token:
        return ""
    
    try:
        events = await google_integration.list_events(
            user.google_access_token, 
            user.google_refresh_token,
            max_results=10
        )
        
        if not events:
            return "\n\nUser's calendar: No upcoming events."
        
        event_list = []
        for event in events:
            event_id = event.get('id', '')
            summary = event.get('summary', 'Untitled')
            start = event.get('start', {})
            start_time = start.get('dateTime', start.get('date', ''))
            
            # Parse and format the time nicely
            try:
                if 'T' in start_time:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    formatted = dt.strftime('%A %B %d at %I:%M %p')
                else:
                    formatted = start_time
            except:
                formatted = start_time
            
            event_list.append(f"  - event_id=\"{event_id}\" title=\"{summary}\" time=\"{formatted}\"")
        
        return "\n\nUser's upcoming calendar events:\n" + "\n".join(event_list) + "\n\nIMPORTANT: When referencing events, use ONLY the value inside event_id quotes (e.g., just 'abc123', not 'event_id=abc123')."
    except Exception as e:
        print(f"Failed to fetch calendar: {e}")
        return ""

@router.post("/clear-history")
async def clear_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Clear conversation history for the current user"""
    await db.execute(
        delete(Interaction).where(Interaction.user_id == user.id)
    )
    await db.commit()
    return {"status": "cleared"}

async def get_conversation_history(db: AsyncSession, user_id: str, limit: int = 10) -> list:
    """Fetch recent conversation history for the user"""
    result = await db.execute(
        select(Interaction)
        .where(Interaction.user_id == user_id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    interactions = result.scalars().all()
    
    # Reverse to get chronological order and format for LLM
    history = []
    for interaction in reversed(interactions):
        history.append({
            "user": interaction.user_message,
            "assistant": interaction.assistant_response
        })
    return history

@router.post("/process", response_model=IntentResponse)
async def process_utterance(
    request: UtteranceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Fetch conversation history
    history = await get_conversation_history(db, user.id)
    
    # Check if this might be about calendar - fetch events for context
    calendar_keywords = ['move', 'reschedule', 'change', 'cancel', 'delete', 'update', 'meeting', 'event', 'calendar', 'schedule']
    text_lower = request.text.lower()
    
    calendar_context = ""
    if any(keyword in text_lower for keyword in calendar_keywords):
        calendar_context = await get_user_calendar_context(user)
    
    result = await parse_utterance(request.text, request.current_time, history, request.timezone or "UTC", calendar_context)
    
    # Handle list_reminders intent specially
    if result.get("intent") == "list_reminders":
        reminders_text = await get_user_reminders_text(db, user.id)
        result["response"] = reminders_text
        result["requires_confirmation"] = False
    
    # Save interaction
    interaction = Interaction(
        user_id=user.id,
        user_message=request.text,
        assistant_response=result.get("response", ""),
        intent=result.get("intent"),
        entities=result.get("entities")
    )
    db.add(interaction)
    await db.commit()
    
    action_id = None
    requires_confirmation = result.get("requires_confirmation", False)
    
    # Check if this is a multi-action response
    actions_list = result.get("actions")
    
    if requires_confirmation:
        action_id = str(uuid.uuid4())
        store_pending_action(
            action_id=action_id,
            user_id=str(user.id),
            intent=result.get("intent", "multi_action" if actions_list else "small_talk"),
            entities=result.get("entities", {}),
            actions=actions_list  # Pass the actions array for multi-action support
        )
    
    return IntentResponse(
        intent=result.get("intent", "multi_action" if actions_list else "small_talk"),
        entities=result.get("entities", {}),
        response=result.get("response", "I understood your request."),
        requires_confirmation=requires_confirmation,
        action_id=action_id
    )

@router.post("/voice", response_model=IntentResponse)
async def process_voice(
    audio: UploadFile = File(...),
    current_time: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    audio_data = await audio.read()
    text = await transcribe_audio(audio_data)
    
    # Fetch conversation history
    history = await get_conversation_history(db, user.id)
    
    result = await parse_utterance(text, current_time, history)
    
    interaction = Interaction(
        user_id=user.id,
        user_message=text,
        assistant_response=result.get("response", ""),
        intent=result.get("intent"),
        entities=result.get("entities")
    )
    db.add(interaction)
    await db.commit()
    
    action_id = None
    requires_confirmation = result.get("requires_confirmation", False)
    actions_list = result.get("actions")
    
    if requires_confirmation:
        action_id = str(uuid.uuid4())
        store_pending_action(
            action_id=action_id,
            user_id=str(user.id),
            intent=result.get("intent", "multi_action" if actions_list else "small_talk"),
            entities=result.get("entities", {}),
            actions=actions_list
        )
    
    return IntentResponse(
        intent=result.get("intent", "multi_action" if actions_list else "small_talk"),
        entities=result.get("entities", {}),
        response=result.get("response", "I understood your request."),
        requires_confirmation=requires_confirmation,
        action_id=action_id
    )

