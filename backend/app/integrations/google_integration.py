from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Optional, List
import base64
import re
from ..core.config import get_settings
from ..core.security import encrypt_token, decrypt_token

settings = get_settings()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify"  # Read, compose, and send emails from your Gmail account
]

def get_auth_flow() -> Flow:
    """Get Google OAuth flow. Raises error if credentials are not configured."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file."
        )
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri
    )

def get_auth_url(state: str = None) -> str:
    """Get Google OAuth authorization URL. Raises error if credentials are not configured."""
    flow = get_auth_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", state=state)
    return auth_url

async def exchange_code(code: str) -> dict:
    flow = get_auth_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials
    return {
        "access_token": encrypt_token(credentials.token),
        "refresh_token": encrypt_token(credentials.refresh_token) if credentials.refresh_token else None,
        "raw_token": credentials.token  # For immediate use to fetch user info
    }

async def get_user_info(access_token: str) -> dict:
    """Get user profile info from Google."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()

def get_credentials(access_token: str, refresh_token: Optional[str] = None) -> Credentials:
    return Credentials(
        token=decrypt_token(access_token),
        refresh_token=decrypt_token(refresh_token) if refresh_token else None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret
    )

# Calendar functions
async def list_events(access_token: str, refresh_token: str, max_results: int = 10) -> List[dict]:
    creds = get_credentials(access_token, refresh_token)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    
    now = datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    return events_result.get("items", [])

async def create_event(
    access_token: str,
    refresh_token: str,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    attendees: List[str] = None,
    description: str = ""
) -> dict:
    creds = get_credentials(access_token, refresh_token)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
    }
    
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]
    
    return service.events().insert(calendarId="primary", body=event).execute()

async def update_event(
    access_token: str,
    refresh_token: str,
    event_id: str,
    updates: dict
) -> dict:
    creds = get_credentials(access_token, refresh_token)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    
    # Get the existing event
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    
    # Apply updates carefully (don't just overwrite nested dicts)
    for key, value in updates.items():
        event[key] = value
    
    # Use patch instead of update to only change specified fields
    return service.events().patch(calendarId="primary", eventId=event_id, body=updates).execute()


async def add_attendees_to_event(
    access_token: str,
    refresh_token: str,
    event_id: str,
    new_attendees: List[str]
) -> dict:
    """Add attendees to an existing event."""
    creds = get_credentials(access_token, refresh_token)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    
    # Get the existing event
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    
    # Get existing attendees and add new ones
    existing_attendees = event.get("attendees", [])
    existing_emails = {a.get("email") for a in existing_attendees}
    
    for email in new_attendees:
        if email not in existing_emails:
            existing_attendees.append({"email": email})
    
    # Update the event with new attendees
    return service.events().patch(
        calendarId="primary", 
        eventId=event_id, 
        body={"attendees": existing_attendees},
        sendUpdates="all"  # Send invite emails
    ).execute()


async def cancel_event(
    access_token: str,
    refresh_token: str,
    event_id: str,
    send_notifications: bool = True
) -> dict:
    """Cancel/delete a calendar event."""
    creds = get_credentials(access_token, refresh_token)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    
    # Get event info before deleting for confirmation message
    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        event_summary = event.get("summary", "Untitled event")
    except:
        event_summary = "the event"
    
    # Delete the event
    service.events().delete(
        calendarId="primary", 
        eventId=event_id,
        sendUpdates="all" if send_notifications else "none"
    ).execute()
    
    return {"status": "cancelled", "summary": event_summary}

# Gmail functions
async def send_email(
    access_token: str,
    refresh_token: str,
    to: str,
    subject: str,
    body: str
) -> dict:
    import base64
    from email.mime.text import MIMEText
    
    creds = get_credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()

async def create_draft(
    access_token: str,
    refresh_token: str,
    to: str,
    subject: str,
    body: str
) -> dict:
    import base64
    from email.mime.text import MIMEText
    
    creds = get_credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

# Gmail email reading functions
def extract_email_body(payload: dict) -> str:
    """Extract email body text from Gmail message payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            body_data = part.get('body', {}).get('data', '')
            
            if mime_type == 'text/plain' and body_data:
                try:
                    body += base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                except:
                    pass
            elif mime_type == 'text/html' and body_data and not body:
                try:
                    html_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                    # Simple HTML tag removal for plain text preview
                    body = re.sub('<[^<]+?>', '', html_body)
                except:
                    pass
    elif payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
        try:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        except:
            pass
    
    return body[:500]  # Limit to 500 chars for preview

async def list_emails(
    access_token: str,
    refresh_token: str,
    max_results: int = 20,
    unread_only: bool = False
) -> List[dict]:
    """
    Fetch emails from Gmail.
    """
    creds = get_credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    
    query = "is:unread" if unread_only else ""
    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = results.get("messages", [])
    emails = []
    
    for msg in messages:
        try:
            message = service.users().messages().get(userId="me", id=msg["id"], format='full').execute()
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            
            email_data = {
                "id": msg["id"],
                "subject": next((h["value"] for h in headers if h["name"] == "Subject"), ""),
                "from": next((h["value"] for h in headers if h["name"] == "From"), ""),
                "date": next((h["value"] for h in headers if h["name"] == "Date"), ""),
                "snippet": message.get("snippet", ""),
                "body": extract_email_body(payload),
                "unread": "UNREAD" in message.get("labelIds", [])
            }
            emails.append(email_data)
        except Exception as e:
            print(f"Error fetching email {msg.get('id')}: {e}")
            continue
    
    return emails

async def get_email_count(access_token: str, refresh_token: str, unread_only: bool = False) -> int:
    """
    Get count of emails (unread or total).
    Uses pagination to get accurate count, with reasonable limits for performance.
    """
    creds = get_credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    
    query = "is:unread" if unread_only else ""
    
    try:
        # First, get an estimate to see if we need to count
        initial_results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=1
        ).execute()
        
        estimate = initial_results.get("resultSizeEstimate", 0)
        
        # For unread emails, always count accurately (even if estimate is large)
        # This ensures accurate counts for the daily digest
        if unread_only:
            # Count accurately for unread emails
            total_count = 0
            page_token = None
            
            while True:
                request_params = {
                    "userId": "me",
                    "q": query,
                    "maxResults": 500  # Maximum allowed by Gmail API
                }
                if page_token:
                    request_params["pageToken"] = page_token
                
                results = service.users().messages().list(**request_params).execute()
                messages = results.get("messages", [])
                total_count += len(messages)
                
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
                
                # Safety limit: stop after 20 pages (10,000 emails) to avoid infinite loops
                if total_count >= 10000:
                    break
            
            return total_count
        else:
            # For total emails, use estimate if large (> 100)
            if estimate < 100:
                # Count accurately for small numbers
                total_count = 0
                page_token = None
                
                while True:
                    request_params = {
                        "userId": "me",
                        "q": query,
                        "maxResults": 500
                    }
                    if page_token:
                        request_params["pageToken"] = page_token
                    
                    results = service.users().messages().list(**request_params).execute()
                    messages = results.get("messages", [])
                    total_count += len(messages)
                    
                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break
                
                return total_count
            else:
                # For large counts, use estimate
                return estimate
    except Exception as e:
        print(f"Error getting email count: {e}")
        # Fallback to estimate if counting fails
        try:
            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=1
            ).execute()
            return results.get("resultSizeEstimate", 0)
        except:
            return 0

async def mark_emails_as_read(
    access_token: str,
    refresh_token: str,
    email_ids: List[str] = None,
    mark_all: bool = False
) -> dict:
    """
    Mark emails as read in Gmail.
    If email_ids is provided, mark only those emails.
    If mark_all is True, mark all unread emails as read.
    """
    creds = get_credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    
    if mark_all:
        # Get all unread email IDs
        results = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=500  # Gmail API limit
        ).execute()
        email_ids = [msg["id"] for msg in results.get("messages", [])]
    
    if not email_ids:
        return {"status": "no_emails", "count": 0}
    
    # Mark each email as read (remove UNREAD label)
    marked_count = 0
    for email_id in email_ids:
        try:
            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            marked_count += 1
        except Exception as e:
            print(f"Error marking email {email_id} as read: {e}")
            continue
    
    return {"status": "marked_read", "count": marked_count}

async def delete_emails(
    access_token: str,
    refresh_token: str,
    email_ids: List[str] = None,
    label: str = None,
    subject_search: str = None,
    delete_count: int = None,
    permanent: bool = False
) -> dict:
    """
    Delete emails in Gmail.
    If email_ids is provided, delete those specific emails.
    If label is provided, delete emails from that label (e.g., "Promotions" or "category_promotions").
    If subject_search is provided, delete emails matching that subject.
    If delete_count is provided, limit to that many emails.
    If permanent is True, permanently delete (defaults to False, which moves to trash).
    """
    creds = get_credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    
    # If no email_ids provided, search for emails to delete
    if not email_ids:
        query_parts = []
        
        # Build search query
        if label:
            # Convert common label names to Gmail label format
            label_map = {
                "promotions": "category_promotions",
                "promotion": "category_promotions",
                "social": "category_social",
                "updates": "category_updates",
                "forums": "category_forums",
            }
            label_lower = label.lower()
            gmail_label = label_map.get(label_lower, label)
            # Handle category labels or regular labels
            if gmail_label.startswith("category_"):
                query_parts.append(f"in:{gmail_label}")
            else:
                query_parts.append(f"label:{gmail_label}")
        
        if subject_search:
            query_parts.append(f'subject:"{subject_search}"')
        
        query = " ".join(query_parts) if query_parts else ""
        
        # Get messages matching the query
        max_results = delete_count if delete_count else 500
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()
        
        email_ids = [msg["id"] for msg in results.get("messages", [])]
    
    if not email_ids:
        return {"status": "no_emails", "count": 0}
    
    # Limit to delete_count if specified
    if delete_count and len(email_ids) > delete_count:
        email_ids = email_ids[:delete_count]
    
    # Delete each email (trash or permanent delete)
    deleted_count = 0
    for email_id in email_ids:
        try:
            if permanent:
                service.users().messages().delete(userId="me", id=email_id).execute()
            else:
                service.users().messages().trash(userId="me", id=email_id).execute()
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting email {email_id}: {e}")
            continue
    
    action = "permanently deleted" if permanent else "moved to trash"
    return {"status": "deleted", "count": deleted_count, "action": action}


