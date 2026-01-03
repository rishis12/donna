from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
import uuid

from ..schemas import ActionConfirm, IntentResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...services import reminder_service
from ...integrations import google_integration, microsoft_integration
from ...integrations.slack_integration import slack_integration
from ...models.messaging_account import MessagingAccount
from ...calendar.conflicts import find_conflict
from ...crud.memory import get_active_memories_for_user
from sqlalchemy import select
from typing import List
import pytz

router = APIRouter(prefix="/action", tags=["action"])

# In-memory storage for pending actions (in production, use Redis or database)
pending_actions: Dict[str, Dict[str, Any]] = {}


class ConflictException(Exception):
    """Exception raised when a calendar conflict is detected."""
    def __init__(self, event_title: str, conflict_event: dict, requested_start: datetime, requested_duration: int):
        self.event_title = event_title
        self.conflict_event = conflict_event
        self.requested_start = requested_start
        self.requested_duration = requested_duration
        super().__init__(f"Conflict with event: {event_title}")


async def _fetch_events_for_day(user: User, target_date: datetime, exclude_event_id: Optional[str] = None) -> List[dict]:
    """
    Fetch calendar events for a specific day and format them for conflict checking.
    
    Args:
        user: User object with access tokens
        target_date: The date to fetch events for
        exclude_event_id: Optional event ID to exclude from the results (e.g., when moving an event)
    
    Returns:
        List of formatted event dictionaries with 'start' and 'end' as datetime objects
    """
    if not user.google_access_token:
        return []
    
    try:
        # Fetch events for the target day (start of day to end of day)
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Use Google Calendar API to fetch events for the day
        creds = google_integration.get_credentials(user.google_access_token, user.google_refresh_token)
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        
        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day.isoformat() + "Z",
            timeMax=end_of_day.isoformat() + "Z",
            maxResults=100,  # Get up to 100 events for the day
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        raw_events = events_result.get("items", [])
        
        # Format events for conflict checking
        formatted_events = []
        for e in raw_events:
            # Skip the event we're moving (if provided)
            if exclude_event_id and e.get('id') == exclude_event_id:
                continue
            
            start_data = e.get('start', {})
            end_data = e.get('end', {})
            
            # Get start and end times
            start_str = start_data.get('dateTime') or start_data.get('date', '')
            end_str = end_data.get('dateTime') or end_data.get('date', '')
            
            if not start_str or not end_str:
                continue
            
            try:
                # Parse to datetime objects
                if 'T' in start_str:
                    event_start = date_parser.parse(start_str)
                else:
                    # All-day event - convert to datetime at start of day
                    event_start = datetime.strptime(start_str, '%Y-%m-%d')
                
                if 'T' in end_str:
                    event_end = date_parser.parse(end_str)
                else:
                    # All-day event - convert to datetime at end of day
                    event_end = datetime.strptime(end_str, '%Y-%m-%d')
                
                formatted_events.append({
                    'id': e.get('id'),
                    'start': event_start,
                    'end': event_end,
                    'summary': e.get('summary', 'Untitled')
                })
            except (ValueError, TypeError):
                # Skip events we can't parse
                continue
        
        return formatted_events
    except Exception as e:
        print(f"Error fetching events for conflict check: {e}")
        return []


def _get_user_preferences(db: AsyncSession, user_id: str) -> dict:
    """
    Fetch user preferences for work_hours, default_meeting_duration, and personality_tone.
    
    Returns:
        dict with 'work_hours', 'default_meeting_duration', and 'personality_tone' keys, or None values if not set
    """
    preferences = {
        'work_hours': None,
        'default_meeting_duration': None,
        'personality_tone': None  # 0.0 = formal, 1.0 = spunky
    }
    
    try:
        memories = db.run_sync(lambda sync_db: get_active_memories_for_user(sync_db, user_id))
        for memory in memories:
            if memory.key == "work_hours":
                preferences['work_hours'] = memory.value
            elif memory.key == "default_meeting_duration":
                preferences['default_meeting_duration'] = memory.value
            elif memory.key == "personality_tone":
                preferences['personality_tone'] = memory.value
    except Exception as e:
        print(f"Error fetching user preferences: {e}")
    
    return preferences


def _is_within_work_hours(time: datetime, work_hours: dict) -> bool:
    """
    Check if a datetime is within the user's work hours.
    
    Args:
        time: datetime to check
        work_hours: dict with 'start', 'end', and 'timezone' keys (e.g., {"start": "09:00", "end": "17:00", "timezone": "America/New_York"})
    
    Returns:
        True if within work hours, False otherwise
    """
    if not work_hours:
        return True  # No work hours restriction
    
    try:
        start_str = work_hours.get('start', '09:00')
        end_str = work_hours.get('end', '17:00')
        tz_str = work_hours.get('timezone', 'UTC')
        
        # Parse start and end times (format: "HH:MM")
        start_hour, start_minute = map(int, start_str.split(':'))
        end_hour, end_minute = map(int, end_str.split(':'))
        
        # Get timezone
        user_tz = pytz.timezone(tz_str) if tz_str else pytz.UTC
        
        # Convert time to user's timezone
        if time.tzinfo is None:
            time = pytz.UTC.localize(time)
        local_time = time.astimezone(user_tz)
        
        # Get time of day in minutes
        time_minutes = local_time.hour * 60 + local_time.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        
        # Handle cases where work hours span midnight
        if start_minutes <= end_minutes:
            return start_minutes <= time_minutes <= end_minutes
        else:
            # Work hours span midnight (e.g., 22:00 - 02:00)
            return time_minutes >= start_minutes or time_minutes <= end_minutes
    except Exception as e:
        print(f"Error checking work hours: {e}")
        return True  # Default to allowing if we can't parse


def _find_next_available_slot(events: List[dict], search_from: datetime, duration_minutes: int, search_until_hours: int = 8, work_hours: Optional[dict] = None) -> Optional[datetime]:
    """
    Find the next available time slot of the specified duration.
    
    Args:
        events: List of events with 'start' and 'end' datetime objects
        search_from: The time to start searching from (typically after a conflicting event)
        duration_minutes: Duration of the slot needed in minutes
        search_until_hours: How many hours ahead to search (default 8 hours)
        work_hours: Optional dict with 'start', 'end', 'timezone' to restrict suggestions to work hours
    
    Returns:
        datetime of the next available slot, or None if none found
    """
    if not events:
        return search_from
    
    # Sort events by start time
    sorted_events = sorted(events, key=lambda e: e.get('start', datetime.min))
    
    # End time for the search window
    search_end = search_from + timedelta(hours=search_until_hours)
    
    # Start checking from the search_from time
    current_check = search_from
    
    for event in sorted_events:
        event_start = event.get('start')
        event_end = event.get('end')
        
        if not event_start or not event_end:
            continue
        
        # Skip events that end before our search start
        if event_end <= current_check:
            continue
        
        # If current check time is before this event, check if we can fit before it
        if current_check < event_start:
            slot_end = current_check + timedelta(minutes=duration_minutes)
            if slot_end <= event_start and slot_end <= search_end:
                # Check if the slot is within work hours (if defined)
                if work_hours and not _is_within_work_hours(current_check, work_hours):
                    # Skip this slot, move to after the event
                    current_check = event_end
                    continue
                return current_check
        
        # Move current_check to after this event
        if current_check < event_end:
            current_check = event_end
    
    # Check if there's time after the last event
    if current_check < search_end:
        slot_end = current_check + timedelta(minutes=duration_minutes)
        if slot_end <= search_end:
            # Check if the slot is within work hours (if defined)
            if work_hours and not _is_within_work_hours(current_check, work_hours):
                return None
            return current_check
    
    return None

def store_pending_action(action_id: str, user_id: str, intent: str, entities: dict, actions: list = None):
    """Store a pending action that requires user confirmation."""
    pending_actions[action_id] = {
        "user_id": user_id,
        "intent": intent,
        "entities": entities,
        "actions": actions,  # For multi-action support
        "created_at": datetime.now(timezone.utc)
    }

def get_pending_action(action_id: str, user_id: str) -> dict | None:
    """Get a pending action by ID, checking user ownership."""
    action = pending_actions.get(action_id)
    if not action:
        return None
    # Check user ownership
    if action.get("user_id") != str(user_id):
        return None
    # Check if expired (older than 1 hour)
    if (datetime.now(timezone.utc) - action["created_at"]).total_seconds() > 3600:
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
        # Check if result is a request_clarification (conflict detected)
        if isinstance(result, dict) and result.get("intent") == "request_clarification":
            return {"status": "clarification_needed", "intent": "request_clarification", "response": result.get("response"), "requires_confirmation": False}
        return {"status": "executed", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def execute_single_action(db: AsyncSession, user: User, intent: str, entities: dict) -> dict:
    """Execute a single action based on intent."""
    if intent == "create_reminder":
        return await execute_create_reminder(db, user, entities)
    elif intent == "schedule_event":
        try:
            return await execute_create_event(user, entities, db)
        except ConflictException as e:
            # Get user preferences
            preferences = _get_user_preferences(db, str(user.id))
            default_duration = preferences.get('default_meeting_duration', {}).get('minutes', 30)
            work_hours = preferences.get('work_hours')
            
            # Find next available slot using default duration
            existing_events = await _fetch_events_for_day(user, e.requested_start)
            # Search from after the conflicting event ends, or from requested start if event end is not available
            search_from = e.conflict_event.get('end')
            if not search_from:
                search_from = e.requested_start
            next_slot = _find_next_available_slot(existing_events, search_from, default_duration, work_hours=work_hours)
            
            # Build response with suggestions
            response_parts = [f"You already have '{e.event_title}' at that time."]
            
            if next_slot:
                # Format the next available time nicely
                if isinstance(next_slot, datetime):
                    time_str = next_slot.strftime('%I:%M %p')
                    # Check if it's today or tomorrow
                    now = datetime.now(next_slot.tzinfo) if next_slot.tzinfo else datetime.now()
                    if next_slot.date() == now.date():
                        date_str = "today"
                    elif next_slot.date() == (now + timedelta(days=1)).date():
                        date_str = "tomorrow"
                    else:
                        date_str = next_slot.strftime('%A, %B %d')
                    duration_text = f"{default_duration}-minute" if default_duration != 30 else "30-minute"
                    response_parts.append(f"Next available {duration_text} slot: {date_str} at {time_str}.")
            
            # Suggest moving the conflicting event
            conflict_event_id = e.conflict_event.get('id')
            if conflict_event_id:
                response_parts.append(f"Or I can move '{e.event_title}' to make room.")
            
            response_parts.append("What would you like to do?")
            
            return {
                "intent": "request_clarification",
                "response": " ".join(response_parts),
                "requires_confirmation": False
            }
    elif intent == "move_event":
        try:
            return await execute_move_event(user, entities, db)
        except ConflictException as e:
            # Get user preferences
            preferences = _get_user_preferences(db, str(user.id))
            default_duration = preferences.get('default_meeting_duration', {}).get('minutes', 30)
            work_hours = preferences.get('work_hours')
            
            # Find next available slot using default duration
            existing_events = await _fetch_events_for_day(user, e.requested_start)
            # Search from after the conflicting event ends, or from requested start if event end is not available
            search_from = e.conflict_event.get('end')
            if not search_from:
                search_from = e.requested_start
            next_slot = _find_next_available_slot(existing_events, search_from, default_duration, work_hours=work_hours)
            
            # Build response with suggestions
            response_parts = [f"You already have '{e.event_title}' at that time."]
            
            if next_slot:
                # Format the next available time nicely
                if isinstance(next_slot, datetime):
                    time_str = next_slot.strftime('%I:%M %p')
                    # Check if it's today or tomorrow
                    now = datetime.now(next_slot.tzinfo) if next_slot.tzinfo else datetime.now()
                    if next_slot.date() == now.date():
                        date_str = "today"
                    elif next_slot.date() == (now + timedelta(days=1)).date():
                        date_str = "tomorrow"
                    else:
                        date_str = next_slot.strftime('%A, %B %d')
                    duration_text = f"{default_duration}-minute" if default_duration != 30 else "30-minute"
                    response_parts.append(f"Next available {duration_text} slot: {date_str} at {time_str}.")
            
            # Suggest moving the conflicting event
            conflict_event_id = e.conflict_event.get('id')
            if conflict_event_id:
                response_parts.append(f"Or I can move '{e.event_title}' to make room.")
            
            response_parts.append("What would you like to do?")
            
            return {
                "intent": "request_clarification",
                "response": " ".join(response_parts),
                "requires_confirmation": False
            }
    elif intent == "update_event":
        return await execute_update_event(user, entities)
    elif intent == "cancel_event":
        return await execute_cancel_event(user, entities)
    elif intent == "draft_email":
        return await execute_draft_email(user, entities)
    elif intent == "send_email":
        return await execute_send_email(user, entities)
    elif intent == "mark_emails_read":
        return await execute_mark_emails_read(user, entities)
    elif intent == "delete_emails":
        return await execute_delete_emails(user, entities)
    elif intent == "send_slack_message":
        return await execute_send_slack_message(db, user, entities)
    elif intent == "send_teams_message":
        return await execute_send_teams_message(user, entities)
    elif intent == "update_user_preference":
        return await execute_update_user_preference(db, user, entities)
    else:
        raise Exception(f"Unknown intent: {intent}")


async def execute_create_reminder(db: AsyncSession, user: User, entities: dict) -> dict:
    """Create a reminder from parsed entities."""
    # Support both LLM output format (text) and legacy format (reminder_text/body)
    text = entities.get("text") or entities.get("reminder_text") or entities.get("body")
    if not text:
        raise Exception("Reminder text is required. What should I remind you about?")
    
    # Support both LLM output format (due_time) and legacy format (time/date)
    time_str = entities.get("due_time") or entities.get("time") or entities.get("date")
    if not time_str:
        raise Exception("Reminder time is required. When should I remind you?")
    
    try:
        due_time = date_parser.parse(time_str)
    except Exception as e:
        raise Exception(f"Could not parse time '{time_str}'. Please specify a valid date and time.")
    
    # Convert to UTC and remove timezone info (database uses TIMESTAMP WITHOUT TIME ZONE)
    if due_time.tzinfo is not None:
        due_time = due_time.astimezone(timezone.utc).replace(tzinfo=None)
    
    # Validate time is in the future
    if due_time <= datetime.utcnow():
        raise Exception("Reminder time must be in the future. Please specify a future time.")
    
    reminder = await reminder_service.create_reminder(
        db,
        user.id,
        text,
        due_time
    )
    
    return {
        "reminder_id": str(reminder.id),
        "text": reminder.text,
        "due_time": reminder.due_time.isoformat()
    }


async def execute_create_event(user: User, entities: dict, db: Optional[AsyncSession] = None) -> dict:
    """Create a calendar event from parsed entities."""
    if not user.google_access_token:
        raise Exception("Google Calendar not connected. Please connect your Google account in Settings.")
    
    # Support both LLM output format (summary) and legacy format (event_title/subject)
    summary = entities.get("summary") or entities.get("event_title") or entities.get("subject")
    if not summary:
        raise Exception("Meeting title is required. Please specify what the meeting is about.")
    
    # Support both LLM output format (start_time) and legacy format (time/date)
    start_str = entities.get("start_time") or entities.get("time") or entities.get("date")
    if not start_str:
        raise Exception("Meeting time is required. Please specify when the meeting should be scheduled.")
    
    try:
        start_time = date_parser.parse(start_str)
    except Exception as e:
        raise Exception(f"Could not parse time '{start_str}'. Please specify a valid date and time.")
    
    # Support both LLM output format (end_time) and legacy format (duration_minutes)
    end_str = entities.get("end_time")
    if end_str:
        try:
            end_time = date_parser.parse(end_str)
            # Calculate duration from start and end times
            duration = int((end_time - start_time).total_seconds() / 60)
        except Exception:
            # Fallback to duration if end_time parsing fails
            duration = entities.get("duration_minutes", 30)
            end_time = start_time + timedelta(minutes=duration)
    else:
        duration = entities.get("duration_minutes", 30)
        end_time = start_time + timedelta(minutes=duration)
    
    # Check for conflicts before scheduling
    existing_events = await _fetch_events_for_day(user, start_time)
    conflict = find_conflict(existing_events, start_time, duration)
    if conflict:
        conflict_summary = conflict.get('summary', 'an existing event')
        raise ConflictException(conflict_summary, conflict, start_time, duration)
    
    # Validate attendees are email addresses if provided
    attendees = entities.get("attendees", [])
    if attendees:
        for attendee in attendees:
            if attendee and "@" not in attendee:
                raise Exception(f"'{attendee}' is not a valid email address. Please provide email addresses for attendees.")
    
    # Support both LLM output format (description) and legacy format (body)
    description = entities.get("description") or entities.get("body", "")
    
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


async def execute_move_event(user: User, entities: dict, db: Optional[AsyncSession] = None) -> dict:
    """Move/update a calendar event."""
    if not user.google_access_token:
        raise Exception("Google Calendar not connected. Please connect your Google account in Settings.")
    
    event_id = entities.get("event_id")
    if not event_id:
        raise Exception("I couldn't identify which event to move. Please try again and specify the event name or time.")
    
    # Support both LLM output format (new_start_time) and legacy format (time)
    new_time_str = entities.get("new_start_time") or entities.get("time")
    if not new_time_str:
        raise Exception("I need to know the new time for this event. What time would you like to move it to?")
    
    try:
        new_time = date_parser.parse(new_time_str)
    except Exception as e:
        raise Exception(f"Could not parse time '{new_time_str}'. Please specify a valid date and time.")
    
    # Get the original event to preserve duration
    try:
        creds = google_integration.get_credentials(user.google_access_token, user.google_refresh_token)
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        orig_event = service.events().get(calendarId="primary", eventId=event_id).execute()
        
        orig_start = orig_event.get("start", {}).get("dateTime", orig_event.get("start", {}).get("date", ""))
        orig_end = orig_event.get("end", {}).get("dateTime", orig_event.get("end", {}).get("date", ""))
        
        try:
            orig_start_dt = date_parser.parse(orig_start)
            orig_end_dt = date_parser.parse(orig_end)
            duration = orig_end_dt - orig_start_dt
        except:
            duration = timedelta(minutes=entities.get("duration_minutes", 30))
    except Exception as e:
        duration = timedelta(minutes=entities.get("duration_minutes", 30))
    
    # Support LLM output format (new_end_time) or calculate from duration
    new_end_time_str = entities.get("new_end_time")
    if new_end_time_str:
        try:
            end_time = date_parser.parse(new_end_time_str)
        except Exception:
            end_time = new_time + duration
    else:
        end_time = new_time + duration
    
    # Check for conflicts before moving (exclude the event we're moving)
    duration_minutes = int(duration.total_seconds() / 60)
    existing_events = await _fetch_events_for_day(user, new_time, exclude_event_id=event_id)
    conflict = find_conflict(existing_events, new_time, duration_minutes)
    if conflict:
        conflict_summary = conflict.get('summary', 'an existing event')
        raise ConflictException(conflict_summary, conflict, new_time, duration_minutes)
    
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
    """Create an email draft (NOT send it)."""
    if not user.google_access_token:
        raise Exception("Gmail not connected")
    
    # Try multiple possible entity names for recipient
    to = (entities.get("to") or 
          entities.get("recipient") or 
          entities.get("email") or
          (entities.get("attendees", [""])[0] if isinstance(entities.get("attendees"), list) and entities.get("attendees") else ""))
    subject = entities.get("subject", "No subject")
    body = entities.get("body") or entities.get("email_body") or entities.get("message") or ""
    
    if not to:
        raise Exception("Email recipient is required")
    
    # Create draft in Gmail (this does NOT send it)
    draft = await google_integration.create_draft(
        user.google_access_token,
        user.google_refresh_token,
        to,
        subject,
        body
    )
    return {
        "draft_id": draft.get("id"),
        "status": "drafted",
        "to": to,
        "subject": subject,
        "body": body,  # Include body in response for email sending
        "message": f"Draft created! Check your Gmail drafts folder. To: {to}, Subject: {subject}"
    }


async def execute_send_email(user: User, entities: dict) -> dict:
    """Send an email."""
    if not user.google_access_token:
        raise Exception("Gmail not connected")
    
    # Try multiple possible entity names for recipient
    to = (entities.get("to") or 
          entities.get("recipient") or 
          entities.get("email") or
          (entities.get("attendees", [""])[0] if isinstance(entities.get("attendees"), list) and entities.get("attendees") else ""))
    subject = entities.get("subject", "")
    body = entities.get("body") or entities.get("email_body") or entities.get("message") or ""
    
    result = await google_integration.send_email(
        user.google_access_token,
        user.google_refresh_token,
        to,
        subject,
        body
    )
    return {"message_id": result.get("id"), "status": "sent"}


async def execute_mark_emails_read(user: User, entities: dict) -> dict:
    """Mark emails as read."""
    if not user.google_access_token:
        raise Exception("Gmail not connected")
    
    mark_all = entities.get("mark_all", False) or entities.get("all", False)
    email_ids = entities.get("email_ids", [])
    
    result = await google_integration.mark_emails_as_read(
        user.google_access_token,
        user.google_refresh_token,
        email_ids if not mark_all else None,
        mark_all=mark_all
    )
    
    return {
        "status": result.get("status"),
        "count": result.get("count", 0),
        "message": f"Marked {result.get('count', 0)} email{'s' if result.get('count', 0) != 1 else ''} as read."
    }


async def execute_delete_emails(user: User, entities: dict) -> dict:
    """Delete emails from Gmail."""
    if not user.google_access_token:
        raise Exception("Gmail not connected")
    
    email_ids = entities.get("email_ids", [])
    label = entities.get("label")
    subject_search = entities.get("subject_search")
    delete_count = entities.get("delete_count")
    permanent = entities.get("permanent", False)
    
    result = await google_integration.delete_emails(
        user.google_access_token,
        user.google_refresh_token,
        email_ids if email_ids else None,
        label=label,
        subject_search=subject_search,
        delete_count=delete_count,
        permanent=permanent
    )
    
    action = result.get("action", "deleted")
    count = result.get("count", 0)
    return {
        "status": result.get("status"),
        "count": count,
        "message": f"{action.capitalize()} {count} email{'s' if count != 1 else ''}."
    }


async def execute_send_slack_message(db: AsyncSession, user: User, entities: dict) -> dict:
    """Send a message to a Slack channel."""
    # Get message content
    message = entities.get("message") or entities.get("slack_message") or entities.get("body")
    if not message:
        raise Exception("Message content is required. What would you like to send to Slack?")
    
    # Get channel - can be channel name (#channel-name) or channel ID
    channel = entities.get("channel") or entities.get("channel_id")
    if not channel:
        raise Exception("Slack channel is required. Which channel should I send the message to? (e.g., #general)")
    
    # Remove # if present (Slack API accepts both formats)
    if channel.startswith("#"):
        channel = channel[1:]
    
    # Get user's Slack messaging account
    result = await db.execute(
        select(MessagingAccount)
        .where(MessagingAccount.user_id == user.id)
        .where(MessagingAccount.platform == "slack")
        .where(MessagingAccount.is_active == True)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise Exception("Slack is not connected. Please connect your Slack workspace in Settings.")
    
    # Get bot token (from account or settings)
    from ...core.config import get_settings
    from ...core.security import decrypt_token
    settings = get_settings()
    
    bot_token = None
    if account.bot_token:
        try:
            bot_token = decrypt_token(account.bot_token)
        except:
            pass
    
    # Fallback to settings token if account token unavailable
    if not bot_token:
        bot_token = settings.slack_bot_token
    
    if not bot_token:
        raise Exception("Slack bot token not configured. Please set up your Slack integration.")
    
    # Try to resolve channel name to ID if it's not already an ID
    # Channel IDs in Slack start with 'C' (public), 'G' (private), 'D' (DM), 'M' (multiparty DM)
    channel_id = channel
    if not (channel.startswith('C') or channel.startswith('G') or channel.startswith('D') or channel.startswith('M')):
        # It's a channel name, try to resolve it
        # For now, we'll try using the name directly (Slack API accepts channel names)
        # In production, you might want to cache channel name -> ID mappings
        channel_id = channel
    
    # Send the message
    try:
        response = await slack_integration.send_message(
            bot_token,
            channel_id,
            message
        )
        
        # Check if message was sent successfully
        if response.get("ok"):
            return {
                "status": "sent",
                "channel": channel,
                "message": message,
                "ts": response.get("ts"),  # Message timestamp
                "response": f"Message sent to #{channel if not channel.startswith(('C', 'G', 'D', 'M')) else 'channel'}"
            }
        else:
            error = response.get("error", "Unknown error")
            raise Exception(f"Failed to send Slack message: {error}")
            
    except Exception as e:
        # Provide helpful error messages
        error_msg = str(e)
        if "channel_not_found" in error_msg or "not_in_channel" in error_msg:
            raise Exception(f"Channel '{channel}' not found or bot is not a member. Please invite the bot to the channel or check the channel name.")
        elif "invalid_auth" in error_msg or "account_inactive" in error_msg:
            raise Exception("Slack authentication failed. Please reconnect your Slack account.")
        else:
            raise Exception(f"Failed to send Slack message: {error_msg}")


async def execute_send_teams_message(user: User, entities: dict) -> dict:
    """Send a message to a Microsoft Teams chat."""
    # Get message content
    message = entities.get("message") or entities.get("teams_message") or entities.get("body")
    if not message:
        raise Exception("Message content is required. What would you like to send to Teams?")
    
    # Get chat ID (required for Teams)
    chat_id = entities.get("chat_id")
    if not chat_id:
        raise Exception("Teams chat ID is required. Which Teams chat should I send the message to? (You can find the chat ID in the Teams URL or by listing your chats)")
    
    # Check if Microsoft is connected
    if not user.microsoft_access_token:
        raise Exception("Microsoft Teams is not connected. Please connect your Microsoft account in Settings.")
    
    # Send the message
    try:
        result = await microsoft_integration.send_teams_message(
            user.microsoft_access_token,
            chat_id,
            message
        )
        
        return {
            "status": "sent",
            "chat_id": chat_id,
            "message": message,
            "message_id": result.get("message_id"),
            "response": "Message sent to Teams chat successfully."
        }
        
    except Exception as e:
        # Provide helpful error messages
        error_msg = str(e)
        if "401" in error_msg or "403" in error_msg or "InvalidAuthenticationToken" in error_msg:
            raise Exception("Microsoft authentication failed. Please reconnect your Microsoft account.")
        elif "404" in error_msg or "NotFound" in error_msg:
            raise Exception(f"Teams chat '{chat_id}' not found. Please check the chat ID and try again.")
        else:
            raise Exception(f"Failed to send Teams message: {error_msg}")


async def execute_update_user_preference(db: AsyncSession, user: User, entities: dict) -> dict:
    """Update or create a user preference in memory."""
    from ...crud.memory import upsert_memory
    
    await db.run_sync(lambda sync_db: upsert_memory(
        sync_db,
        user_id=str(user.id),
        key=entities.get("preference_key"),
        type_="preference",
        value=entities.get("preference_value", {})
    ))
    
    return {
        "status": "updated",
        "message": "Preference saved successfully."
    }


# API endpoint for updating personality preference
@router.post("/preferences/personality")
async def update_personality_preference(
    tone: float = Query(..., ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Update personality tone preference.
    tone: 0.0 (formal) to 1.0 (spunky)
    """
    from ...crud.memory import upsert_memory
    
    # Validate tone range
    if tone < 0.0 or tone > 1.0:
        raise HTTPException(status_code=400, detail="Tone must be between 0.0 and 1.0")
    
    await db.run_sync(lambda sync_db: upsert_memory(
        sync_db,
        user_id=str(user.id),
        key="personality_tone",
        type_="preference",
        value={"tone": float(tone)}
    ))
    
    return {
        "status": "updated",
        "message": "Personality preference saved successfully.",
        "tone": tone
    }


@router.get("/preferences/personality")
async def get_personality_preference(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get current personality tone preference."""
    from ...crud.memory import get_active_memories_for_user
    
    try:
        memories = await db.run_sync(lambda sync_db: get_active_memories_for_user(sync_db, user.id))
        for memory in memories:
            if memory.key == "personality_tone" and memory.value:
                return {
                    "tone": float(memory.value.get("tone", 0.5))
                }
    except Exception as e:
        print(f"Error fetching personality preference: {e}")
    
    # Return default if not found
    return {"tone": 0.5}

    


