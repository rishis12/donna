from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...models.reminder import Reminder, ReminderStatus
from ...integrations import google_integration, microsoft_integration
from ...services.llm_service import summarize_communications
from datetime import datetime, timedelta

router = APIRouter(prefix="/digest", tags=["digest"])

@router.get("/daily")
async def get_daily_digest(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get daily digest: today's meetings, active reminders, and inbox summary."""
    
    # Use UTC for date comparison to match reminder storage (reminders stored in UTC)
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    # Get today's calendar events
    meetings = []
    if user.google_access_token:
        try:
            raw_events = await google_integration.list_events(
                user.google_access_token,
                user.google_refresh_token,
                max_results=20
            )
            for e in raw_events:
                start = e.get('start', {})
                start_time = start.get('dateTime', start.get('date', ''))
                
                # Check if event is today
                try:
                    if 'T' in start_time:
                        event_date = datetime.fromisoformat(start_time.replace('Z', '+00:00')).date()
                    else:
                        event_date = datetime.strptime(start_time, '%Y-%m-%d').date()
                    
                    if event_date == today:
                        end = e.get('end', {})
                        meetings.append({
                            "id": e.get('id'),
                            "summary": e.get('summary', 'Untitled'),
                            "start": start.get('dateTime', start.get('date', '')),
                            "end": end.get('dateTime', end.get('date', '')),
                            "attendees": [a.get('email') for a in e.get('attendees', []) if a.get('email')]
                        })
                except:
                    pass
        except Exception as e:
            print(f"Failed to fetch calendar for digest: {e}")
    
    # Get active reminders for today
    result = await db.execute(
        select(Reminder)
        .where(Reminder.user_id == user.id)
        .where(Reminder.status == ReminderStatus.ACTIVE)
        .order_by(Reminder.due_time)
    )
    all_reminders = result.scalars().all()
    
    reminders = []
    for r in all_reminders:
        if r.due_time.date() == today:
            # Append Z to indicate UTC timezone for proper client-side parsing
            due_time_iso = r.due_time.isoformat() + "Z"
            reminders.append({
                "id": str(r.id),
                "text": r.text,
                "dueTime": due_time_iso
            })
    
    # Get email and Teams message counts and summaries
    unread_emails_gmail = 0
    unread_emails_outlook = 0
    unread_teams = 0
    communications_summary = ""
    
    try:
        # Gmail unread count
        if user.google_access_token:
            unread_emails_gmail = await google_integration.get_email_count(
                user.google_access_token,
                user.google_refresh_token,
                unread_only=True
            )
        
        # Outlook unread count
        if user.microsoft_access_token:
            try:
                unread_emails_outlook = await microsoft_integration.get_email_count(
                    user.microsoft_access_token,
                    unread_only=True
                )
            except Exception as e:
                print(f"Error getting Outlook email count: {e}")
                unread_emails_outlook = 0
            
            try:
                unread_teams = await microsoft_integration.get_teams_message_count(
                    user.microsoft_access_token,
                    unread_only=True
                )
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
                        unread_teams = await microsoft_integration.get_teams_message_count(
                            user.microsoft_access_token,
                            unread_only=True
                        )
                    except Exception as refresh_error:
                        print(f"Error refreshing Microsoft token: {refresh_error}")
                        unread_teams = 0
                else:
                    print(f"Error getting Teams message count: {e}")
                    unread_teams = 0
            except Exception as e:
                print(f"Error getting Teams message count: {e}")
                unread_teams = 0
        
        # Get communications summary if there are unread items
        total_unread = unread_emails_gmail + unread_emails_outlook + unread_teams
        if total_unread > 0:
            emails = []
            teams_messages = []
            
            if unread_emails_gmail > 0 and user.google_access_token:
                try:
                    gmail_emails = await google_integration.list_emails(
                        user.google_access_token,
                        user.google_refresh_token,
                        max_results=10,
                        unread_only=True
                    )
                    emails.extend([{**e, "provider": "gmail"} for e in gmail_emails])
                except:
                    pass
            
            if unread_emails_outlook > 0 and user.microsoft_access_token:
                try:
                    outlook_emails = await microsoft_integration.list_emails(
                        user.microsoft_access_token,
                        max_results=10,
                        unread_only=True
                    )
                    emails.extend([{**e, "provider": "outlook"} for e in outlook_emails])
                    print(f"Fetched {len(outlook_emails)} Outlook emails for digest")
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
                                max_results=10,
                                unread_only=True
                            )
                            emails.extend([{**e, "provider": "outlook"} for e in outlook_emails])
                            print(f"Fetched {len(outlook_emails)} Outlook emails after token refresh")
                        except Exception as refresh_error:
                            print(f"Error refreshing Microsoft token for Outlook emails: {refresh_error}")
                    else:
                        print(f"Error fetching Outlook emails: {e}")
                except Exception as e:
                    print(f"Error fetching Outlook emails: {e}")
            
            if unread_teams > 0 and user.microsoft_access_token:
                try:
                    teams_messages = await microsoft_integration.list_teams_messages(
                        user.microsoft_access_token,
                        max_results=10,
                        unread_only=True
                    )
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
                            teams_messages = await microsoft_integration.list_teams_messages(
                                user.microsoft_access_token,
                                max_results=10,
                                unread_only=True
                            )
                        except Exception as refresh_error:
                            print(f"Error refreshing Microsoft token for Teams messages: {refresh_error}")
                            teams_messages = []
                    else:
                        print(f"Error fetching Teams messages: {e}")
                        teams_messages = []
                except Exception as e:
                    print(f"Error fetching Teams messages: {e}")
                    teams_messages = []
            
            if emails or teams_messages:
                communications_summary = await summarize_communications(emails, teams_messages)
    except Exception as e:
        print(f"Failed to fetch communications summary: {e}")
    
    total_unread_emails = unread_emails_gmail + unread_emails_outlook
    
    return {
        "date": today.isoformat(),
        "meetings": meetings,
        "meetingsCount": len(meetings),
        "reminders": reminders,
        "remindersCount": len(reminders),
        "unreadEmails": total_unread_emails,
        "unreadEmailsGmail": unread_emails_gmail,
        "unreadEmailsOutlook": unread_emails_outlook,
        "unreadTeams": unread_teams,
        "communicationsSummary": communications_summary,
        "summary": _generate_digest_summary(meetings, reminders, total_unread_emails, unread_teams)
    }

def _generate_digest_summary(meetings: list, reminders: list, unread_emails: int, unread_teams: int) -> str:
    """Generate a natural language summary of the daily digest."""
    parts = []
    
    if len(meetings) > 0:
        if len(meetings) == 1:
            meeting = meetings[0]
            start_time = meeting.get("start", "")
            try:
                if 'T' in start_time:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%I:%M %p')
                    parts.append(f"1 meeting at {time_str}: {meeting.get('summary', 'Untitled')}")
                else:
                    parts.append(f"1 meeting today: {meeting.get('summary', 'Untitled')}")
            except:
                parts.append(f"1 meeting today: {meeting.get('summary', 'Untitled')}")
        else:
            parts.append(f"{len(meetings)} meetings scheduled")
    else:
        parts.append("no meetings")
    
    if len(reminders) > 0:
        if len(reminders) == 1:
            reminder = reminders[0]
            try:
                due_time_str = reminder.get("dueTime", "")
                # Handle both with and without Z suffix
                if due_time_str.endswith('Z'):
                    due_dt = datetime.fromisoformat(due_time_str.replace('Z', '+00:00'))
                else:
                    due_dt = datetime.fromisoformat(due_time_str)
                time_str = due_dt.strftime('%I:%M %p')
                parts.append(f"1 reminder at {time_str}: {reminder.get('text', '')}")
            except:
                parts.append(f"1 reminder: {reminder.get('text', '')}")
        else:
            parts.append(f"{len(reminders)} reminders")
    else:
        parts.append("no reminders")
    
    if unread_emails > 0 or unread_teams > 0:
        comm_parts = []
        if unread_emails > 0:
            comm_parts.append(f"{unread_emails} unread email{'s' if unread_emails != 1 else ''}")
        if unread_teams > 0:
            comm_parts.append(f"{unread_teams} unread Teams message{'s' if unread_teams != 1 else ''}")
        parts.append(", ".join(comm_parts))
    else:
        parts.append("all caught up on communications")
    
    return f"Today you have {', '.join(parts)}."

