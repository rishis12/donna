from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import httpx
from ..schemas import UtteranceRequest, IntentResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...models.interaction import Interaction
from ...models.reminder import Reminder, ReminderStatus
from ...models.messaging_account import MessagingAccount
from ...services.llm_service import parse_utterance, transcribe_audio
from ...integrations import google_integration, microsoft_integration
from ...services.llm_service import summarize_communications
from ...integrations import google_integration
from .action import store_pending_action, execute_mark_emails_read, execute_delete_emails
import uuid
from datetime import datetime, timezone

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
    
    result = await parse_utterance(
        request.text, 
        request.current_time, 
        history, 
        request.timezone or "UTC", 
        calendar_context,
        db=db,
        user_id=str(user.id)
    )
    
    # Handle list_reminders intent specially
    if result.get("intent") == "list_reminders":
        reminders_text = await get_user_reminders_text(db, user.id)
        result["response"] = reminders_text
        result["requires_confirmation"] = False
    
    # Handle update_user_preference intent - execute immediately without confirmation
    if result.get("intent") == "update_user_preference":
        try:
            from .action import execute_update_user_preference
            action_result = await execute_update_user_preference(db, user, result.get("entities", {}))
            result["response"] = action_result.get("message", "Preference saved successfully.")
            result["requires_confirmation"] = False
        except Exception as e:
            result["response"] = f"I couldn't save that preference: {str(e)}"
            result["requires_confirmation"] = False
    
    # Handle mark_emails_read intent - execute immediately without confirmation
    if result.get("intent") == "mark_emails_read":
        if not user.google_access_token:
            result["response"] = "Gmail is not connected. Please connect your Gmail account in Settings."
            result["requires_confirmation"] = False
        else:
            try:
                entities = result.get("entities", {})
                action_result = await execute_mark_emails_read(user, entities)
                result["response"] = action_result.get("message", f"Marked {action_result.get('count', 0)} email(s) as read.")
                result["requires_confirmation"] = False
            except Exception as e:
                result["response"] = f"I couldn't mark the emails as read: {str(e)}"
                result["requires_confirmation"] = False
    
    # Handle delete_emails intent - requires confirmation for safety
    if result.get("intent") == "delete_emails":
        if not user.google_access_token:
            result["response"] = "Gmail is not connected. Please connect your Gmail account in Settings."
            result["requires_confirmation"] = False
        else:
            # Set requires_confirmation to True so user confirms before deleting
            entities = result.get("entities", {})
            delete_count = entities.get("delete_count")
            label = entities.get("label")
            subject_search = entities.get("subject_search")
            permanent = entities.get("permanent", False)
            
            # Build confirmation message
            action_desc = []
            if label:
                action_desc.append(f"from '{label}' inbox")
            if subject_search:
                action_desc.append(f"with subject containing '{subject_search}'")
            if delete_count:
                action_desc.append(f"the last {delete_count}")
            else:
                action_desc.append("all matching")
            
            action_word = "permanently delete" if permanent else "delete"
            result["response"] = f"I'll {action_word} {' '.join(action_desc)} email(s). This action cannot be undone. Should I proceed?"
            result["requires_confirmation"] = True
    
    # Handle draft_email intent - generate email content and show preview
    if result.get("intent") == "draft_email":
        entities = result.get("entities", {})
        # Try multiple possible entity names for recipient
        to = (entities.get("to") or 
              entities.get("recipient") or 
              entities.get("email") or
              (entities.get("attendees", [""])[0] if isinstance(entities.get("attendees"), list) and entities.get("attendees") else ""))
        subject_hint = entities.get("subject", "")
        body_context = entities.get("body") or entities.get("email_body") or entities.get("message") or ""
        
        # Check if recipient is an email address (contains @)
        if to and "@" not in to:
            result["response"] = f"I need {to}'s email address to send the email. Could you provide their email address?"
            result["requires_confirmation"] = False
        elif to:
            from ...services.llm_service import draft_email_content
            try:
                # Combine all context for the email generation
                full_context = body_context
                if result.get("response") and "brief" in result.get("response", "").lower():
                    full_context += " Keep it brief."
                if result.get("response") and ("no dear" in result.get("response", "").lower() or "without dear" in result.get("response", "").lower()):
                    full_context += " No 'Dear' greeting - start directly with the message."
                if result.get("response") and "donna" in result.get("response", "").lower():
                    full_context += ' Include "Sent with Donna" tagline.'
                
                email_content = await draft_email_content(to, subject_hint, full_context)
                generated_subject = email_content.get("subject", subject_hint or "No subject")
                generated_body = email_content.get("body", body_context or "")
                
                # Update entities with generated content
                result["entities"]["to"] = to
                result["entities"]["subject"] = generated_subject
                result["entities"]["body"] = generated_body
                
                # Create preview response
                preview = f"📧 Email Draft:\n\nTo: {to}\nSubject: {generated_subject}\n\n{generated_body}\n\nWould you like me to create this draft?"
                result["response"] = preview
                result["requires_confirmation"] = True
            except Exception as e:
                print(f"Error generating email draft: {e}")
                result["response"] = "I had trouble generating the email. Could you provide more details?"
                result["requires_confirmation"] = False
        else:
            result["response"] = "I need to know who to send the email to. Please provide the recipient's email address."
            result["requires_confirmation"] = False
    
    # Handle summarize_communications intent
    if result.get("intent") == "summarize_communications":
        emails = []
        teams_messages = []
        slack_messages = []
        api_available = False
        
        # Fetch Gmail emails
        if user.google_access_token:
            try:
                gmail_emails = await google_integration.list_emails(
                    user.google_access_token,
                    user.google_refresh_token,
                    max_results=15,
                    unread_only=True
                )
                # Check if API is actually implemented (not just placeholder returning empty array)
                if len(gmail_emails) > 0:
                    api_available = True
                    emails.extend([{**e, "provider": "gmail"} for e in gmail_emails])
            except Exception as e:
                print(f"Failed to fetch Gmail: {e}")
        
        # Fetch Outlook emails
        if user.microsoft_access_token:
            try:
                outlook_emails = await microsoft_integration.list_emails(
                    user.microsoft_access_token,
                    max_results=15,
                    unread_only=True
                )
                if len(outlook_emails) > 0:
                    api_available = True
                    emails.extend([{**e, "provider": "outlook"} for e in outlook_emails])
                    print(f"Fetched {len(outlook_emails)} Outlook emails")
            except httpx.HTTPStatusError as e:
                # Token expired - try to refresh
                if e.response.status_code == 401 and user.microsoft_refresh_token:
                    try:
                        new_tokens = await microsoft_integration.refresh_access_token(
                            user.microsoft_refresh_token
                        )
                        user.microsoft_access_token = new_tokens["access_token"]
                        if new_tokens.get("refresh_token"):
                            user.microsoft_refresh_token = new_tokens["refresh_token"]
                        await db.commit()
                        
                        # Retry with new token
                        outlook_emails = await microsoft_integration.list_emails(
                            user.microsoft_access_token,
                            max_results=15,
                            unread_only=True
                        )
                        if len(outlook_emails) > 0:
                            api_available = True
                            emails.extend([{**e, "provider": "outlook"} for e in outlook_emails])
                            print(f"Fetched {len(outlook_emails)} Outlook emails after token refresh")
                    except Exception as refresh_error:
                        print(f"Error refreshing Microsoft token for Outlook: {refresh_error}")
                else:
                    print(f"Failed to fetch Outlook: {e}")
            except Exception as e:
                print(f"Failed to fetch Outlook: {e}")
            
            # Fetch Teams messages
            try:
                teams_messages = await microsoft_integration.list_teams_messages(
                    user.microsoft_access_token,
                    max_results=15,
                    unread_only=True
                )
                if len(teams_messages) > 0:
                    api_available = True
            except Exception as e:
                print(f"Failed to fetch Teams: {e}")
        
        # Fetch Slack messages
        from ...core.config import get_settings
        from ...integrations.slack_integration import slack_integration
        from ...core.security import decrypt_token
        settings = get_settings()
        
        try:
            # Get user's Slack messaging account (from OAuth connection)
            result_accounts = await db.execute(
                select(MessagingAccount)
                .where(MessagingAccount.platform == "slack")
                .where(MessagingAccount.is_active == True)
                .where(MessagingAccount.user_id == user.id)
            )
            accounts = result_accounts.scalars().all()
            
            print(f"[SLACK] Found {len(accounts)} Slack account(s) for user {user.id}")
            
            # Try to get bot token from user's account first, fallback to settings
            bot_token = None
            for account in accounts:
                if account.bot_token:
                    try:
                        bot_token = decrypt_token(account.bot_token)
                        print(f"[SLACK] Using bot token from account {account.id}")
                        break
                    except Exception as e:
                        print(f"[SLACK] Failed to decrypt token from account {account.id}: {e}")
                        pass
            
            # Fallback to settings token if no account token
            if not bot_token:
                bot_token = settings.slack_bot_token
                if bot_token:
                    print(f"[SLACK] Using bot token from settings")
            
            if not bot_token:
                print(f"[SLACK] No bot token available - Slack not configured")
            else:
                print(f"[SLACK] Fetching recent messages with token: {bot_token[:10]}...")
                # Fetch recent messages from all channels
                recent_messages = await slack_integration.get_recent_messages(bot_token, max_messages=30)
                print(f"[SLACK] Fetched {len(recent_messages)} messages")
                
                for msg in recent_messages:
                    slack_messages.append({
                        "channel": msg.get("channel_id", ""),
                        "channel_name": msg.get("channel_name", ""),
                        "user": msg.get("user", ""),
                        "username": msg.get("username", msg.get("user", "")),  # Use resolved username
                        "text": msg.get("text", ""),
                        "timestamp": datetime.fromtimestamp(float(msg.get("ts", 0)), tz=timezone.utc).isoformat() if msg.get("ts") else "",
                        "message_id": msg.get("ts", "")
                    })
                
                if len(recent_messages) > 0:
                    api_available = True
                    print(f"[SLACK] Added {len(slack_messages)} Slack messages to summary")
        except Exception as e:
            print(f"[SLACK] Failed to fetch Slack messages: {e}")
            import traceback
            traceback.print_exc()
        
        # If APIs are not implemented (return empty), use LLM's response directly
        if not api_available and (len(emails) == 0 and len(teams_messages) == 0 and len(slack_messages) == 0):
            # Use the LLM's response since it might have context from the conversation
            # Don't override it with "No new emails" since the LLM may have detected emails
            result["response"] = result.get("response", "Email APIs are not yet implemented. Please check your inbox manually.")
            result["requires_confirmation"] = False
        else:
            # Generate summary from actual data
            summary = await summarize_communications(emails, teams_messages, slack_messages)
            result["response"] = summary
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
    
    result = await parse_utterance(
        text, 
        current_time, 
        history,
        db=db,
        user_id=str(user.id)
    )
    
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

