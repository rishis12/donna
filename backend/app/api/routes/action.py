from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import uuid

from ..schemas import ActionConfirm, IntentResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...services import reminder_service
from ...integrations import google_integration, microsoft_integration

router = APIRouter(prefix="/action", tags=["action"])

# In-memory store for pending actions (in production, use Redis or DB)
pending_actions: Dict[str, Dict[str, Any]] = {}


def store_pending_action(action_id: str, user_id: str, intent: str, entities: dict, actions: list = None):
    """Store a pending action (or multiple actions) that requires confirmation."""
    pending_actions[action_id] = {
        "user_id": str(user_id),
        "intent": intent,
        "entities": entities,
        "actions": actions,  # For multi-action support
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=5)
    }


def get_pending_action(action_id: str, user_id: str) -> dict | None:
    """Retrieve a pending action if it exists and belongs to the user."""
    action = pending_actions.get(action_id)
    if not action:
        return None
    if action["user_id"] != str(user_id):
        return None
    if datetime.utcnow() > action["expires_at"]:
        del pending_actions[action_id]
        return None
    return action


@router.post("/confirm")
async def confirm_action(
    data: ActionConfirm,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Confirm or cancel a pending action (or multiple actions)."""
    action = get_pending_action(data.action_id, user.id)
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or expired")
    
    # Remove from pending
    del pending_actions[data.action_id]
    
    if not data.confirmed:
        return {"status": "cancelled", "message": "Action was cancelled"}
    
    # Check if this is a multi-action request
    actions_list = action.get("actions")
    if actions_list:
        # Execute multiple actions
        results = []
        errors = []
        for single_action in actions_list:
            try:
                result = await execute_single_action(db, user, single_action["intent"], single_action["entities"])
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        if errors:
            return {"status": "partial", "message": f"Completed {len(results)} actions, {len(errors)} failed: {'; '.join(errors)}", "results": results}
        return {"status": "executed", "message": f"Completed {len(results)} actions successfully!", "results": results}
    
    # Single action
    intent = action["intent"]
    entities = action["entities"]
    
    try:
        result = await execute_single_action(db, user, intent, entities)
        return {"status": "executed", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def execute_single_action(db: AsyncSession, user: User, intent: str, entities: dict) -> dict:
    """Execute a single action based on intent."""
    if intent == "create_reminder":
        return await execute_create_reminder(db, user, entities)
    elif intent == "schedule_event":
        return await execute_create_event(user, entities)
    elif intent == "move_event":
        return await execute_move_event(user, entities)
    elif intent == "update_event":
        return await execute_update_event(user, entities)
    elif intent == "cancel_event":
        return await execute_cancel_event(user, entities)
    elif intent == "draft_email":
        return await execute_draft_email(user, entities)
    elif intent == "send_email":
        return await execute_send_email(user, entities)
    else:
        raise Exception(f"Unknown intent: {intent}")


async def execute_create_reminder(db: AsyncSession, user: User, entities: dict) -> dict:
    """Create a reminder from parsed entities."""
    text = entities.get("reminder_text", entities.get("body"))
    if not text:
        raise Exception("Reminder text is required. What should I remind you about?")
    
    time_str = entities.get("time") or entities.get("date")
    if not time_str:
        raise Exception("Reminder time is required. When should I remind you?")
    
    try:
        due_time = date_parser.parse(time_str)
    except Exception as e:
        raise Exception(f"Could not parse time '{time_str}'. Please specify a valid date and time.")
    
    reminder = await reminder_service.create_reminder(db, user.id, text, due_time)
    return {
        "id": str(reminder.id),
        "text": reminder.text,
        "due_time": reminder.due_time.isoformat()
    }


async def execute_create_event(user: User, entities: dict) -> dict:
    """Create a calendar event from parsed entities."""
    if not user.google_access_token:
        raise Exception("Google Calendar not connected. Please connect your Google account in Settings.")
    
    summary = entities.get("event_title", entities.get("subject"))
    if not summary:
        raise Exception("Meeting title is required. Please specify what the meeting is about.")
    
    start_str = entities.get("time") or entities.get("date")
    if not start_str:
        raise Exception("Meeting time is required. Please specify when the meeting should be scheduled.")
    
    try:
        start_time = date_parser.parse(start_str)
    except Exception as e:
        raise Exception(f"Could not parse time '{start_str}'. Please specify a valid date and time.")
    
    duration = entities.get("duration_minutes", 30)
    end_time = start_time + timedelta(minutes=duration)
    
    # Validate attendees are email addresses if provided
    attendees = entities.get("attendees", [])
    if attendees:
        for attendee in attendees:
            if attendee and "@" not in attendee:
                raise Exception(f"'{attendee}' is not a valid email address. Please provide email addresses for attendees.")
    
    description = entities.get("body", "")
    
    event = await google_integration.create_event(
        user.google_access_token,
        user.google_refresh_token,
        summary,
        start_time,
        end_time,
        attendees,
        description
    )
    return {"event_id": event.get("id"), "summary": summary}


async def execute_move_event(user: User, entities: dict) -> dict:
    """Move/update a calendar event."""
    if not user.google_access_token:
        raise Exception("Google Calendar not connected. Please connect your Google account in Settings.")
    
    event_id = entities.get("event_id")
    if not event_id:
        raise Exception("I couldn't identify which event to move. Please try again and specify the event name or time.")
    
    new_time_str = entities.get("time")
    if not new_time_str:
        raise Exception("I need to know the new time for this event. What time would you like to move it to?")
    
    try:
        new_time = date_parser.parse(new_time_str)
    except Exception as e:
        raise Exception(f"Could not parse the new time '{new_time_str}'. Please specify a valid date and time.")
    
    # Get the original event to preserve its duration
    try:
        from ...integrations import google_integration as gi
        creds = gi.get_credentials(user.google_access_token, user.google_refresh_token)
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        original_event = service.events().get(calendarId="primary", eventId=event_id).execute()
        
        # Calculate original duration
        orig_start = original_event.get('start', {}).get('dateTime')
        orig_end = original_event.get('end', {}).get('dateTime')
        if orig_start and orig_end:
            orig_start_dt = date_parser.parse(orig_start)
            orig_end_dt = date_parser.parse(orig_end)
            duration = orig_end_dt - orig_start_dt
        else:
            duration = timedelta(minutes=entities.get("duration_minutes", 30))
    except Exception as e:
        duration = timedelta(minutes=entities.get("duration_minutes", 30))
    
    end_time = new_time + duration
    
    updates = {
        "start": {"dateTime": new_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"}
    }
    
    event = await google_integration.update_event(
        user.google_access_token,
        user.google_refresh_token,
        event_id,
        updates
    )
    
    event_title = event.get("summary", "the event")
    return {
        "event_id": event.get("id"), 
        "status": "moved",
        "message": f"Moved '{event_title}' to {new_time.strftime('%B %d at %I:%M %p')}"
    }


async def execute_update_event(user: User, entities: dict) -> dict:
    """Update an existing calendar event (add attendees, change title, etc.)."""
    if not user.google_access_token:
        raise Exception("Google Calendar not connected. Please connect your Google account in Settings.")
    
    event_id = entities.get("event_id")
    if not event_id:
        raise Exception("I couldn't identify which event to update. Please try again and specify the event name or time.")
    
    attendees = entities.get("attendees", [])
    
    if attendees:
        # Validate attendees are email addresses
        for attendee in attendees:
            if attendee and "@" not in attendee:
                raise Exception(f"'{attendee}' is not a valid email address. Please provide email addresses for attendees.")
        
        # Add attendees to the event
        event = await google_integration.add_attendees_to_event(
            user.google_access_token,
            user.google_refresh_token,
            event_id,
            attendees
        )
        
        event_title = event.get("summary", "the event")
        attendee_names = ", ".join(attendees)
        return {
            "event_id": event.get("id"),
            "status": "updated",
            "message": f"Added {attendee_names} to '{event_title}'. Invites have been sent!"
        }
    else:
        raise Exception("I'm not sure what you want to update. Would you like to add attendees, change the title, or something else?")


async def execute_cancel_event(user: User, entities: dict) -> dict:
    """Cancel/delete one or more calendar events."""
    if not user.google_access_token:
        raise Exception("Google Calendar not connected. Please connect your Google account in Settings.")
    
    # Support both single event_id and multiple event_ids
    event_ids = entities.get("event_ids", [])
    single_id = entities.get("event_id")
    
    if single_id and single_id not in event_ids:
        event_ids.append(single_id)
    
    if not event_ids:
        raise Exception("I couldn't identify which event(s) to cancel. Please specify the event name or time.")
    
    cancelled_events = []
    errors = []
    
    for event_id in event_ids:
        try:
            result = await google_integration.cancel_event(
                user.google_access_token,
                user.google_refresh_token,
                event_id,
                send_notifications=True
            )
            cancelled_events.append(result.get("summary", "event"))
        except Exception as e:
            errors.append(str(e))
    
    if cancelled_events:
        if len(cancelled_events) == 1:
            message = f"Cancelled '{cancelled_events[0]}'. Attendees have been notified."
        else:
            event_names = ", ".join(f"'{e}'" for e in cancelled_events)
            message = f"Cancelled {len(cancelled_events)} events: {event_names}. Attendees have been notified."
        
        if errors:
            message += f" (Some events failed: {len(errors)} errors)"
        
        return {"status": "cancelled", "message": message}
    else:
        raise Exception(f"Failed to cancel events: {'; '.join(errors)}")


async def execute_draft_email(user: User, entities: dict) -> dict:
    """Create an email draft."""
    if not user.google_access_token:
        raise Exception("Gmail not connected")
    
    to = entities.get("attendees", [entities.get("to", "")])[0] if isinstance(entities.get("attendees"), list) else entities.get("to", "")
    subject = entities.get("subject", "")
    body = entities.get("body", "")
    
    draft = await google_integration.create_draft(
        user.google_access_token,
        user.google_refresh_token,
        to,
        subject,
        body
    )
    return {"draft_id": draft.get("id"), "status": "drafted"}


async def execute_send_email(user: User, entities: dict) -> dict:
    """Send an email."""
    if not user.google_access_token:
        raise Exception("Gmail not connected")
    
    to = entities.get("attendees", [entities.get("to", "")])[0] if isinstance(entities.get("attendees"), list) else entities.get("to", "")
    subject = entities.get("subject", "")
    body = entities.get("body", "")
    
    result = await google_integration.send_email(
        user.google_access_token,
        user.google_refresh_token,
        to,
        subject,
        body
    )
    return {"message_id": result.get("id"), "status": "sent"}

