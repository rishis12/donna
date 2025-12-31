import aiohttp
import json
import urllib.parse
from typing import Optional, Dict, List
from datetime import datetime, timezone
from ..core.config import get_settings
from ..core.security import encrypt_token, decrypt_token

settings = get_settings()

# Slack OAuth scopes needed for the app
SLACK_SCOPES = [
    "chat:write",
    "channels:read",
    "groups:read",
    "im:read",
    "mpim:read",
    "channels:history",
    "groups:history",
    "im:history",
    "mpim:history",
    "users:read",
    "app_mentions:read"
]

def get_auth_url(state: str = None) -> str:
    """Generate Slack OAuth authorization URL."""
    if not settings.slack_client_id:
        raise Exception("SLACK_CLIENT_ID is not configured. Please set it in your .env file.")
    
    params = {
        "client_id": settings.slack_client_id,
        "scope": ",".join(SLACK_SCOPES),
        "redirect_uri": settings.slack_redirect_uri,
    }
    if state:
        params["state"] = state
    
    return f"https://slack.com/oauth/v2/authorize?{urllib.parse.urlencode(params)}"

async def exchange_code(code: str) -> dict:
    """Exchange OAuth code for access token."""
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise Exception("Slack OAuth is not configured. Please set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in your .env file.")
    
    url = "https://slack.com/api/oauth.v2.access"
    data = {
        "client_id": settings.slack_client_id,
        "client_secret": settings.slack_client_secret,
        "code": code,
        "redirect_uri": settings.slack_redirect_uri
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            result = await response.json()
            
            if not result.get("ok"):
                error = result.get("error", "Unknown error")
                raise Exception(f"Slack OAuth error: {error}")
            
            # Slack OAuth v2 response structure:
            # - access_token: Bot token (this is what we need)
            # - authed_user.access_token: User token (optional, for user context)
            authed_user = result.get("authed_user", {})
            team = result.get("team", {})
            bot_token = result.get("access_token", "")  # Bot token is in access_token for v2
            user_token = authed_user.get("access_token", "") if authed_user else None
            
            return {
                "access_token": encrypt_token(bot_token),  # Store bot token as access_token
                "user_token": encrypt_token(user_token) if user_token else None,
                "team_id": team.get("id", ""),
                "team_name": team.get("name", ""),
                "user_id": authed_user.get("id", ""),
                "raw_token": bot_token  # For immediate use
            }

async def get_user_info(access_token: str) -> dict:
    """Get user/team info from Slack using bot token."""
    url = "https://slack.com/api/auth.test"
    headers = {"Authorization": f"Bearer {decrypt_token(access_token)}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            result = await response.json()
            
            if not result.get("ok"):
                raise Exception(f"Failed to get Slack user info: {result.get('error')}")
            
            return {
                "team_id": result.get("team_id", ""),
                "team_name": result.get("team", ""),
                "user_id": result.get("user_id", ""),
                "user_name": result.get("user", "")
            }

class SlackIntegration:
    def __init__(self):
        self.base_url = "https://slack.com/api"

    async def send_message(self, bot_token: str, channel: str, text: str, thread_ts: str = None) -> dict:
        """Send a message to a Slack channel."""
        url = f"{self.base_url}/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }

        data = {
            "channel": channel,
            "text": text
        }
        if thread_ts:
            data["thread_ts"] = thread_ts

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                return await response.json()

    async def get_channel_history(self, bot_token: str, channel: str, limit: int = 50) -> dict:
        """Get message history from a Slack channel."""
        url = f"{self.base_url}/conversations.history"
        headers = {"Authorization": f"Bearer {bot_token}"}
        params = {
            "channel": channel,
            "limit": limit
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                return await response.json()

    async def list_channels(self, bot_token: str, types: str = "public_channel,private_channel") -> List[dict]:
        """List all channels the bot has access to."""
        url = f"{self.base_url}/conversations.list"
        headers = {"Authorization": f"Bearer {bot_token}"}
        params = {
            "types": types,
            "exclude_archived": "true",  # Convert boolean to string for URL params
            "limit": "100"  # Convert to string for consistency
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                result = await response.json()
                if result.get("ok"):
                    return result.get("channels", [])
                return []

    async def get_user_info(self, bot_token: str, user_id: str) -> dict:
        """Get user information from Slack user ID."""
        url = f"{self.base_url}/users.info"
        headers = {"Authorization": f"Bearer {bot_token}"}
        params = {"user": user_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                result = await response.json()
                if result.get("ok"):
                    user = result.get("user", {})
                    return {
                        "id": user_id,
                        "name": user.get("real_name") or user.get("name", ""),
                        "display_name": user.get("profile", {}).get("display_name") or user.get("real_name") or user.get("name", ""),
                        "email": user.get("profile", {}).get("email", "")
                    }
                return {"id": user_id, "name": user_id, "display_name": user_id}

    async def get_recent_messages(self, bot_token: str, max_messages: int = 50) -> List[dict]:
        """Get recent messages from all channels the bot has access to."""
        all_messages = []
        user_cache = {}  # Cache user info to avoid repeated API calls
        
        # Get list of channels
        print(f"[SLACK] Listing channels...")
        channels = await self.list_channels(bot_token)
        print(f"[SLACK] Found {len(channels)} channels")
        
        if not channels:
            print(f"[SLACK] No channels found - bot may not be in any channels")
            return []
        
        # Get messages from each channel
        for channel in channels[:10]:  # Limit to first 10 channels to avoid too many API calls
            channel_id = channel.get("id")
            channel_name = channel.get("name", "")
            if not channel_id:
                continue
            
            try:
                print(f"[SLACK] Fetching messages from channel #{channel_name} ({channel_id})")
                history = await self.get_channel_history(bot_token, channel_id, limit=10)
                if history.get("ok"):
                    messages = history.get("messages", [])
                    print(f"[SLACK] Found {len(messages)} messages in #{channel_name}")
                    for msg in messages:
                        # Skip bot messages and system messages
                        if msg.get("bot_id") or msg.get("subtype"):
                            continue
                        
                        user_id = msg.get("user", "")
                        # Get username from cache or fetch it
                        if user_id and user_id not in user_cache:
                            try:
                                user_info = await self.get_user_info(bot_token, user_id)
                                user_cache[user_id] = user_info.get("display_name") or user_info.get("name") or user_id
                            except Exception as e:
                                print(f"[SLACK] Failed to get user info for {user_id}: {e}")
                                user_cache[user_id] = user_id  # Fallback to ID
                        
                        username = user_cache.get(user_id, user_id)
                        
                        all_messages.append({
                            "channel_id": channel_id,
                            "channel_name": channel_name,
                            "user": user_id,
                            "username": username,
                            "text": msg.get("text", ""),
                            "ts": msg.get("ts", ""),
                            "thread_ts": msg.get("thread_ts")
                        })
                else:
                    error = history.get("error", "Unknown error")
                    print(f"[SLACK] Error fetching from #{channel_name}: {error}")
            except Exception as e:
                print(f"[SLACK] Exception fetching messages from channel {channel_id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Sort by timestamp (most recent first) and limit
        all_messages.sort(key=lambda x: float(x.get("ts", 0)), reverse=True)
        print(f"[SLACK] Returning {len(all_messages[:max_messages])} messages (limited from {len(all_messages)})")
        return all_messages[:max_messages]

    async def create_webhook(self, bot_token: str, channel: str) -> dict:
        """Create an incoming webhook for a channel (requires admin permissions)."""
        # This would typically be done through Slack's web interface
        # For API-created webhooks, you'd use the app management API
        pass

    async def post_to_webhook(self, webhook_url: str, text: str, username: str = None) -> dict:
        """Post a message to a Slack webhook."""
        data = {"text": text}
        if username:
            data["username"] = username

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data) as response:
                return await response.json()

    def format_message_for_donna(self, message: dict) -> dict:
        """Format incoming Slack message for Donna processing."""
        user = message.get("user", "")
        ts = message.get("ts", "")

        return {
            "platform": "slack",
            "message_id": message.get("client_msg_id", message.get("ts", "")),
            "channel": message.get("channel"),
            "user_id": user,
            "username": message.get("user", ""),
            "text": message.get("text", ""),
            "timestamp": datetime.fromtimestamp(float(ts), tz=timezone.utc) if ts else datetime.now(timezone.utc),
            "thread_ts": message.get("thread_ts"),
            "files": message.get("files", []),
            "reactions": message.get("reactions", [])
        }

# Global instance
slack_integration = SlackIntegration()
