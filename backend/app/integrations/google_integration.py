from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Optional, List
from ..core.config import get_settings
from ..core.security import encrypt_token, decrypt_token

settings = get_settings()

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose"
]

def get_auth_flow() -> Flow:
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

def get_auth_url() -> str:
    flow = get_auth_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return auth_url

async def exchange_code(code: str) -> dict:
    flow = get_auth_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials
    return {
        "access_token": encrypt_token(credentials.token),
        "refresh_token": encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
    }

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
    service = build("calendar", "v3", credentials=creds)
    
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
    service = build("calendar", "v3", credentials=creds)
    
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
    service = build("calendar", "v3", credentials=creds)
    
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    event.update(updates)
    
    return service.events().update(calendarId="primary", eventId=event_id, body=event).execute()

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
    service = build("gmail", "v1", credentials=creds)
    
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
    service = build("gmail", "v1", credentials=creds)
    
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

