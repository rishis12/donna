from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
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
from sqlalchemy import select
from typing import List

router = APIRouter(prefix="/action", tags=["action"])

# In-memory storage for pending actions (in production, use Redis or database)
pending_actions: Dict[str, Dict[str, Any]] = {}

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
    elif intent == "mark_emails_read":
        return await execute_mark_emails_read(user, entities)
    elif intent == "delete_emails":
        return await execute_delete_emails(user, entities)
    elif intent == "send_slack_message":
        return await execute_send_slack_message(db, user, entities)
    elif intent == "send_teams_message":
        return await execute_send_teams_message(user, entities)
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

    


