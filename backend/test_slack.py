"""
Test script for Slack integration.
Run this to verify your Slack bot token is working correctly.
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

import aiohttp

async def test_slack_token():
    """Test if the Slack bot token is valid."""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    
    if not bot_token:
        print("❌ ERROR: SLACK_BOT_TOKEN not found in .env file")
        return False
    
    print(f"🔑 Testing token: {bot_token[:20]}...")
    
    # Test 1: Verify token with Slack's auth.test endpoint
    print("\n📋 Test 1: Verifying token with Slack API...")
    url = "https://slack.com/api/auth.test"
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("✅ Token is valid!")
                    print(f"   Bot User ID: {result.get('user_id')}")
                    print(f"   Team: {result.get('team')}")
                    print(f"   User: {result.get('user')}")
                    return True
                else:
                    print(f"❌ Token validation failed: {result.get('error')}")
                    if result.get('error') == 'invalid_auth':
                        print("   → Check that your token is correct and hasn't been revoked")
                    elif result.get('error') == 'account_inactive':
                        print("   → Your bot may have been removed from the workspace")
                    return False
    except Exception as e:
        print(f"❌ Error connecting to Slack API: {e}")
        return False

async def test_send_message(channel_id: str = None):
    """Test sending a message to Slack."""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    
    if not bot_token:
        print("❌ ERROR: SLACK_BOT_TOKEN not found in .env file")
        return False
    
    if not channel_id:
        print("\n⚠️  Skipping message test - no channel ID provided")
        print("   To test sending, run: python test_slack.py <channel_id>")
        print("   Example: python test_slack.py C1234567890")
        return True
    
    print(f"\n📤 Test 2: Sending test message to channel {channel_id}...")
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "channel": channel_id,
        "text": "🧪 Test message from Donna AI Assistant! If you see this, the Slack integration is working correctly."
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("✅ Message sent successfully!")
                    print(f"   Message timestamp: {result.get('ts')}")
                    print(f"   Channel: {result.get('channel')}")
                    return True
                else:
                    print(f"❌ Failed to send message: {result.get('error')}")
                    error = result.get('error')
                    if error == 'channel_not_found':
                        print("   → Make sure the bot is invited to the channel")
                        print("   → Channel ID should start with 'C' for public channels")
                    elif error == 'not_in_channel':
                        print("   → The bot needs to be invited to the channel first")
                        print("   → In Slack, type: /invite @YourBotName")
                    elif error == 'missing_scope':
                        print("   → The bot needs 'chat:write' scope")
                        print("   → Add it in your Slack app's OAuth & Permissions settings")
                    return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

async def test_list_channels():
    """Test listing channels (optional)."""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    
    if not bot_token:
        return False
    
    print(f"\n📋 Test 3: Listing channels...")
    
    url = "https://slack.com/api/conversations.list"
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "types": "public_channel,private_channel",
        "limit": 10
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                result = await response.json()
                
                if result.get("ok"):
                    channels = result.get("channels", [])
                    print(f"✅ Found {len(channels)} channels:")
                    for channel in channels[:5]:  # Show first 5
                        print(f"   - #{channel.get('name')} (ID: {channel.get('id')})")
                    if len(channels) > 5:
                        print(f"   ... and {len(channels) - 5} more")
                    return True
                else:
                    print(f"⚠️  Could not list channels: {result.get('error')}")
                    print("   (This is optional - bot may not have channels:read scope)")
                    return True  # Not critical
    except Exception as e:
        print(f"⚠️  Error listing channels: {e}")
        return True  # Not critical

async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Slack Integration Test")
    print("=" * 60)
    
    # Test token
    token_valid = await test_slack_token()
    
    if not token_valid:
        print("\n❌ Token test failed. Please check your SLACK_BOT_TOKEN in .env")
        sys.exit(1)
    
    # Test listing channels (optional)
    await test_list_channels()
    
    # Test sending message if channel ID provided
    channel_id = sys.argv[1] if len(sys.argv) > 1 else None
    if channel_id:
        await test_send_message(channel_id)
    else:
        await test_send_message()  # Will show instructions
    
    print("\n" + "=" * 60)
    print("✅ Testing complete!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Get a channel ID from Slack (right-click channel → View channel details)")
    print("   2. Invite your bot to the channel: /invite @YourBotName")
    print("   3. Test sending: python test_slack.py <channel_id>")
    print("   4. Use the Donna API to send messages via /messaging-accounts/send-message")

if __name__ == "__main__":
    asyncio.run(main())

