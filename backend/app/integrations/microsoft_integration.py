import httpx
from msal import ConfidentialClientApplication
from datetime import datetime
from typing import List, Optional
from ..core.config import get_settings
from ..core.security import encrypt_token, decrypt_token

settings = get_settings()

SCOPES = ["openid", "profile", "email", "User.Read", "Calendars.ReadWrite", "Mail.Send"]
GRAPH_URL = "https://graph.microsoft.com/v1.0"

def get_msal_app() -> ConfidentialClientApplication:
    return ConfidentialClientApplication(
        settings.microsoft_client_id,
        authority="https://login.microsoftonline.com/common",
        client_credential=settings.microsoft_client_secret
    )

def get_auth_url(state: str = None) -> str:
    app = get_msal_app()
    return app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=settings.microsoft_redirect_uri,
        state=state
    )

async def exchange_code(code: str) -> dict:
    app = get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=settings.microsoft_redirect_uri
    )
    
    if "access_token" in result:
        return {
            "access_token": encrypt_token(result["access_token"]),
            "refresh_token": encrypt_token(result.get("refresh_token", "")),
            "raw_token": result["access_token"]  # For immediate use to fetch user info
        }
    raise Exception(result.get("error_description", "Failed to get token"))

async def get_user_info(access_token: str) -> dict:
    """Get user profile info from Microsoft Graph."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GRAPH_URL}/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()
        return {
            "email": data.get("mail") or data.get("userPrincipalName"),
            "name": data.get("displayName"),
            "id": data.get("id")
        }

async def refresh_access_token(refresh_token: str) -> dict:
    app = get_msal_app()
    result = app.acquire_token_by_refresh_token(
        decrypt_token(refresh_token),
        scopes=SCOPES
    )
    
    if "access_token" in result:
        return {
            "access_token": encrypt_token(result["access_token"]),
            "refresh_token": encrypt_token(result.get("refresh_token", refresh_token))
        }
    raise Exception("Failed to refresh token")

# Calendar functions
async def list_events(access_token: str, max_results: int = 10) -> List[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GRAPH_URL}/me/events",
            headers={"Authorization": f"Bearer {decrypt_token(access_token)}"},
            params={"$top": max_results, "$orderby": "start/dateTime"}
        )
        response.raise_for_status()
        return response.json().get("value", [])

async def create_event(
    access_token: str,
    subject: str,
    start_time: datetime,
    end_time: datetime,
    attendees: List[str] = None,
    body: str = ""
) -> dict:
    event = {
        "subject": subject,
        "body": {"contentType": "text", "content": body},
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
    }
    
    if attendees:
        event["attendees"] = [
            {"emailAddress": {"address": email}, "type": "required"}
            for email in attendees
        ]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_URL}/me/events",
            headers={"Authorization": f"Bearer {decrypt_token(access_token)}"},
            json=event
        )
        response.raise_for_status()
        return response.json()

async def update_event(access_token: str, event_id: str, updates: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{GRAPH_URL}/me/events/{event_id}",
            headers={"Authorization": f"Bearer {decrypt_token(access_token)}"},
            json=updates
        )
        response.raise_for_status()
        return response.json()

# Mail functions
async def send_email(access_token: str, to: str, subject: str, body: str) -> dict:
    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_URL}/me/sendMail",
            headers={"Authorization": f"Bearer {decrypt_token(access_token)}"},
            json=message
        )
        response.raise_for_status()
        return {"status": "sent"}

