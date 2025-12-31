import aiohttp
import json
from typing import Optional, Dict, List
from datetime import datetime, timezone
from ..core.config import get_settings
from ..core.security import encrypt_token, decrypt_token

settings = get_settings()

class DiscordIntegration:
    def __init__(self):
        self.base_url = "https://discord.com/api/v10"

    async def send_message(self, bot_token: str, channel_id: str, content: str, embeds: List[dict] = None) -> dict:
        """Send a message to a Discord channel."""
        url = f"{self.base_url}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }

        data = {"content": content}
        if embeds:
            data["embeds"] = embeds

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                return await response.json()

    async def get_channel_messages(self, bot_token: str, channel_id: str, limit: int = 50) -> dict:
        """Get messages from a Discord channel."""
        url = f"{self.base_url}/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {bot_token}"}
        params = {"limit": limit}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                return await response.json()

    async def create_webhook(self, bot_token: str, channel_id: str, name: str) -> dict:
        """Create a webhook in a Discord channel."""
        url = f"{self.base_url}/channels/{channel_id}/webhooks"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }

        data = {"name": name}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                return await response.json()

    async def execute_webhook(self, webhook_id: str, webhook_token: str, content: str, username: str = None) -> dict:
        """Execute a Discord webhook."""
        url = f"{self.base_url}/webhooks/{webhook_id}/{webhook_token}"
        data = {"content": content}
        if username:
            data["username"] = username

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.json()

    def format_message_for_donna(self, message: dict) -> dict:
        """Format incoming Discord message for Donna processing."""
        author = message.get("author", {})
        timestamp = message.get("timestamp", "")

        return {
            "platform": "discord",
            "message_id": message.get("id"),
            "channel_id": message.get("channel_id"),
            "user_id": author.get("id"),
            "username": author.get("username"),
            "discriminator": author.get("discriminator"),
            "text": message.get("content", ""),
            "timestamp": datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if timestamp else datetime.now(timezone.utc),
            "mentions": [mention.get("id") for mention in message.get("mentions", [])],
            "attachments": message.get("attachments", [])
        }

# Global instance
discord_integration = DiscordIntegration()
