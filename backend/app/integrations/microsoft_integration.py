import httpx
from msal import ConfidentialClientApplication
from datetime import datetime
from typing import List, Optional
from ..core.config import get_settings
from ..core.security import encrypt_token, decrypt_token

settings = get_settings()

SCOPES = [
    "User.Read", 
    "Calendars.ReadWrite", 
    "Mail.Send",
    "Mail.Read",  # For reading emails
    "Chat.Read",  # For reading Teams messages
    "ChatMessage.Read",  # For reading Teams chat messages
    "ChatMessage.Send"  # For sending Teams messages
]
# Note: MSAL automatically adds openid, profile, offline_access, and email scopes
GRAPH_URL = "https://graph.microsoft.com/v1.0"

def get_msal_app() -> ConfidentialClientApplication:
    """Get MSAL app instance. Raises error if credentials are not configured."""
    if not settings.microsoft_client_id or not settings.microsoft_client_secret:
        raise ValueError(
            "Microsoft OAuth credentials not configured. "
            "Please set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET in your .env file."
        )
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
    """Exchange authorization code for access token."""
    app = get_msal_app()
    
    # Ensure redirect_uri is set
    if not settings.microsoft_redirect_uri:
        raise ValueError("MICROSOFT_REDIRECT_URI not configured in .env file")
    
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
    
    # Provide more detailed error message
    error = result.get("error", "Unknown error")
    error_description = result.get("error_description", "Failed to get token")
    raise Exception(f"Microsoft OAuth error: {error} - {error_description}")

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

# Outlook email reading functions
async def list_emails(
    access_token: str,
    max_results: int = 20,
    unread_only: bool = False
) -> List[dict]:
    """
    Fetch emails from Outlook using Microsoft Graph API.
    """
    async with httpx.AsyncClient() as client:
        params = {
            "$top": max_results,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,body,bodyPreview,isRead"
        }
        
        if unread_only:
            params["$filter"] = "isRead eq false"
        
        response = await client.get(
            f"{GRAPH_URL}/me/messages",
            headers={"Authorization": f"Bearer {decrypt_token(access_token)}"},
            params=params
        )
        response.raise_for_status()
        messages = response.json().get("value", [])
        
        emails = []
        for msg in messages:
            from_address = msg.get("from", {}).get("emailAddress", {})
            body_content = msg.get("body", {})
            
            emails.append({
                "id": msg.get("id"),
                "subject": msg.get("subject", ""),
                "from": from_address.get("address", ""),
                "date": msg.get("receivedDateTime", ""),
                "body": body_content.get("content", ""),
                "bodyPreview": msg.get("bodyPreview", ""),
                "unread": not msg.get("isRead", True)
            })
        
        return emails

async def get_email_count(access_token: str, unread_only: bool = False) -> int:
    """
    Get count of emails (unread or total) using Microsoft Graph API.
    Uses $count query parameter to get accurate count.
    """
    async with httpx.AsyncClient() as client:
        params = {
            "$top": 0,  # Don't fetch any messages, just get count
            "$count": "true",
            "$select": "id"
        }
        
        if unread_only:
            params["$filter"] = "isRead eq false"
        
        try:
            response = await client.get(
                f"{GRAPH_URL}/me/messages",
                headers={
                    "Authorization": f"Bearer {decrypt_token(access_token)}",
                    "ConsistencyLevel": "eventual",  # Required for $count
                    "Prefer": "odata.maxpagesize=1"  # Minimize data transfer
                },
                params=params
            )
            response.raise_for_status()
            
            # Try to get count from response header first
            count_header = response.headers.get("@odata.count")
            if count_header:
                try:
                    return int(count_header)
                except (ValueError, TypeError):
                    pass
            
            # Fallback: check the @odata.count in response body
            response_data = response.json()
            if "@odata.count" in response_data:
                try:
                    return int(response_data["@odata.count"])
                except (ValueError, TypeError):
                    pass
            
            # If no count available, return 0
            return 0
        except Exception as e:
            print(f"Error getting Outlook email count: {e}")
            return 0

# Microsoft Teams message reading functions
async def list_teams_messages(
    access_token: str,
    max_results: int = 20,
    unread_only: bool = False
) -> List[dict]:
    """
    Fetch messages from Microsoft Teams (chats and channels) using Microsoft Graph API.
    Gets messages from personal chats (1-on-1 and group chats).
    """
    async with httpx.AsyncClient() as client:
        decrypted_token = decrypt_token(access_token)
        headers = {"Authorization": f"Bearer {decrypted_token}"}
        all_messages = []
        
        try:
            # Get personal chats
            # Note: unreadCount is not available in $select for /me/chats endpoint
            chats_response = await client.get(
                f"{GRAPH_URL}/me/chats",
                headers=headers,
                params={
                    "$top": 50,  # Get up to 50 chats
                    "$select": "id,chatType,topic"  # Removed unreadCount - not supported in $select
                }
            )
            
            # Handle 401 Unauthorized - token expired
            if chats_response.status_code == 401:
                raise httpx.HTTPStatusError(
                    "Token expired",
                    request=chats_response.request,
                    response=chats_response
                )
            
            # Handle 400 Bad Request - might be invalid parameters
            if chats_response.status_code == 400:
                # Try without $select to see if that's the issue
                chats_response = await client.get(
                    f"{GRAPH_URL}/me/chats",
                    headers=headers,
                    params={"$top": 50}
                )
                chats_response.raise_for_status()
            
            chats_response.raise_for_status()
            chats = chats_response.json().get("value", [])
            
            # Get messages from each chat
            # Limit to first 10 chats to avoid too many API calls
            for chat in chats[:10]:
                try:
                    chat_id = chat.get("id")
                    if not chat_id:
                        continue
                    
                    # Get messages from this chat
                    messages_params = {
                        "$top": 5,  # Get last 5 messages per chat
                        "$orderby": "createdDateTime desc",
                        "$select": "id,createdDateTime,from,body"
                    }
                    
                    messages_response = await client.get(
                        f"{GRAPH_URL}/me/chats/{chat_id}/messages",
                        headers=headers,
                        params=messages_params
                    )
                    
                    # Handle 401 Unauthorized - token expired
                    if messages_response.status_code == 401:
                        raise httpx.HTTPStatusError(
                            "Token expired",
                            request=messages_response.request,
                            response=messages_response
                        )
                    
                    messages_response.raise_for_status()
                    chat_messages = messages_response.json().get("value", [])
                    
                    # Format messages
                    for msg in chat_messages:
                        from_user = msg.get("from", {}).get("user", {})
                        body_content = msg.get("body", {})
                        
                        # Note: unreadCount is not available on chat object from /me/chats
                        # We'll mark as unread if we're filtering for unread only
                        all_messages.append({
                            "id": msg.get("id"),
                            "from": from_user.get("displayName", "Unknown"),
                            "body": body_content.get("content", ""),
                            "date": msg.get("createdDateTime", ""),
                            "chatId": chat_id,
                            "chatType": chat.get("chatType", "unknown"),
                            "topic": chat.get("topic", ""),
                            "unread": unread_only  # If filtering for unread, assume all are unread
                        })
                        
                        # Stop if we have enough messages
                        if len(all_messages) >= max_results:
                            break
                    
                    if len(all_messages) >= max_results:
                        break
                        
                except Exception as e:
                    # Skip chats that fail (might be permission issues or empty chats)
                    print(f"Error fetching messages from chat {chat.get('id')}: {e}")
                    continue
            
            # Sort by date (most recent first) and limit to max_results
            all_messages.sort(key=lambda x: x.get("date", ""), reverse=True)
            
            # Filter unread if requested
            if unread_only:
                all_messages = [msg for msg in all_messages if msg.get("unread", False)]
            
            return all_messages[:max_results]
            
        except Exception as e:
            print(f"Error fetching Teams messages: {e}")
            # Return empty list on error rather than crashing
            return []

async def get_teams_message_count(access_token: str, unread_only: bool = False) -> int:
    """
    Get count of Teams messages (unread or total) using Microsoft Graph API.
    """
    async with httpx.AsyncClient() as client:
        decrypted_token = decrypt_token(access_token)
        headers = {"Authorization": f"Bearer {decrypted_token}"}
        
        try:
            # Get personal chats
            # Note: unreadCount is not available in $select for /me/chats endpoint
            chats_response = await client.get(
                f"{GRAPH_URL}/me/chats",
                headers=headers,
                params={"$top": 50, "$select": "id"}  # Removed unreadCount - not supported
            )
            
            # Handle 401 Unauthorized - token expired
            if chats_response.status_code == 401:
                raise httpx.HTTPStatusError(
                    "Token expired",
                    request=chats_response.request,
                    response=chats_response
                )
            
            # Handle 400 Bad Request - might be invalid parameters
            if chats_response.status_code == 400:
                # Try without $select to see if that's the issue
                chats_response = await client.get(
                    f"{GRAPH_URL}/me/chats",
                    headers=headers,
                    params={"$top": 50}
                )
                chats_response.raise_for_status()
            
            chats_response.raise_for_status()
            chats = chats_response.json().get("value", [])
            
            if unread_only:
                # Since unreadCount is not available, we need to check messages
                # This is more expensive but necessary for accurate count
                total_unread = 0
                for chat in chats[:10]:  # Limit to first 10 chats for performance
                    try:
                        chat_id = chat.get("id")
                        if not chat_id:
                            continue
                        # Get unread messages count for this chat
                        messages_response = await client.get(
                            f"{GRAPH_URL}/me/chats/{chat_id}/messages",
                            headers=headers,
                            params={
                                "$top": 1,
                                "$filter": "isRead eq false",
                                "$count": "true"
                            }
                        )
                        if messages_response.status_code == 200:
                            # Try to get count from header or response
                            count_header = messages_response.headers.get("@odata.count")
                            if count_header:
                                total_unread += int(count_header)
                    except Exception:
                        continue
                return total_unread
            else:
                # For total count, we'd need to iterate through all messages
                # This is expensive, so we return the number of chats as an approximation
                return len(chats)
                
        except Exception as e:
            print(f"Error fetching Teams message count: {e}")
            return 0

# Microsoft Teams message sending function
async def send_teams_message(
    access_token: str,
    chat_id: str,
    message: str
) -> dict:
    """
    Send a message to a Microsoft Teams chat using Microsoft Graph API.
    
    Args:
        access_token: Encrypted Microsoft access token
        chat_id: The ID of the Teams chat to send the message to
        message: The message content to send
        
    Returns:
        dict with message ID and status
    """
    async with httpx.AsyncClient() as client:
        decrypted_token = decrypt_token(access_token)
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }
        
        # Format message body for Teams
        message_body = {
            "body": {
                "contentType": "text",
                "content": message
            }
        }
        
        response = await client.post(
            f"{GRAPH_URL}/me/chats/{chat_id}/messages",
            headers=headers,
            json=message_body
        )
        response.raise_for_status()
        result = response.json()
        
        return {
            "message_id": result.get("id"),
            "chat_id": chat_id,
            "status": "sent"
        }
