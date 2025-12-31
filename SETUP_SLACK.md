# Slack Integration Setup Guide

This guide walks you through setting up Slack integration for Donna, allowing you to interact with Donna through Slack messages.

## Overview

Donna's Slack integration supports two methods:
1. **Slack Bot** - Using a Bot Token (recommended for production)
2. **Slack Webhook** - Using incoming webhooks (simpler, but limited)

## Prerequisites

- A Slack workspace where you have admin permissions (or can install apps)
- Your Donna backend server running and accessible (for webhooks, you'll need a public URL)
- Access to your `.env` file

---

## Method 1: Slack Bot Setup (Recommended)

This method uses Slack's Bot Token and provides full API access.

### Step 1: Create a Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter:
   - **App Name**: `Donna AI Assistant` (or your preferred name)
   - **Pick a workspace**: Select your workspace
5. Click **"Create App"**

### Step 2: Configure Bot Token Scopes

1. In your app settings, go to **"OAuth & Permissions"** (left sidebar)
2. Scroll down to **"Scopes"** → **"Bot Token Scopes"**
3. Add the following scopes:
   - `chat:write` - Send messages as the bot
   - `channels:history` - View messages in public channels
   - `groups:history` - View messages in private channels
   - `im:history` - View messages in direct messages
   - `mpim:history` - View messages in group direct messages
   - `channels:read` - View basic information about public channels
   - `groups:read` - View basic information about private channels
   - `users:read` - View people in a workspace
   - `app_mentions:read` - Subscribe to bot mentions (optional, for @mentions)

### Step 3: Install App to Workspace

1. Scroll to the top of **"OAuth & Permissions"**
2. Click **"Install to Workspace"**
3. Review the permissions and click **"Allow"**
4. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`)
   - This is your `SLACK_BOT_TOKEN`

### Step 4: Configure Event Subscriptions (Optional, for Webhooks)

If you want Donna to receive messages via webhooks:

1. Go to **"Event Subscriptions"** (left sidebar)
2. Enable **"Enable Events"**
3. Set **Request URL** to: `https://your-domain.com/messaging-accounts/webhook/slack`
   - Replace `your-domain.com` with your actual domain
   - For local development, use ngrok: `https://your-ngrok-url.ngrok-free.app/messaging-accounts/webhook/slack`
4. Under **"Subscribe to bot events"**, add:
   - `message.channels` - Messages posted to channels
   - `message.groups` - Messages posted to private channels
   - `message.im` - Direct messages
   - `message.mpim` - Group direct messages
5. Click **"Save Changes"**
6. Slack will verify your URL - make sure your server is running and accessible

### Step 5: Configure Signing Secret (Required for Webhooks)

1. Go to **"Basic Information"** (left sidebar)
2. Under **"App Credentials"**, find **"Signing Secret"**
3. Click **"Show"** and copy the secret
   - This is your `SLACK_SIGNING_SECRET`
   - **Important**: This is required for webhook signature verification

### Step 6: Add Environment Variables

Add to your `.env` file:

```env
# Slack Bot Token (from Step 3)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Slack Signing Secret (from Step 5, REQUIRED for webhooks)
SLACK_SIGNING_SECRET=your-signing-secret-here

# Your public webhook URL (for webhooks)
SLACK_WEBHOOK_BASE_URL=https://your-domain.com
```

**Note**: The signing secret is required for webhook security. Without it, webhook requests will be rejected.

### Step 7: Invite Bot to Channel

1. In Slack, go to the channel where you want to use Donna
2. Type `/invite @Donna AI Assistant` (or your bot name)
3. Or go to channel settings → **"Integrations"** → **"Add apps"** → Find your bot

---

## Method 2: Incoming Webhook Setup (Simpler)

This method is simpler but more limited - it only allows sending messages, not receiving them.

### Step 1: Create Incoming Webhook

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app or use an existing one
3. Go to **"Incoming Webhooks"** (left sidebar)
4. Enable **"Activate Incoming Webhooks"**
5. Click **"Add New Webhook to Workspace"**
6. Select the channel where you want messages posted
7. Click **"Allow"**
8. **Copy the Webhook URL** (starts with `https://hooks.slack.com/services/...`)

### Step 2: Add to Donna

You can add this webhook URL when creating a messaging account via the API:

```bash
POST /messaging-accounts/
{
  "platform": "slack",
  "account_id": "your-channel-id",
  "account_name": "My Slack Channel",
  "channel_id": "C1234567890",  # Channel ID (optional)
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

---

## Using the Integration

### Option A: Via API

#### 1. Add a Messaging Account

```bash
POST /messaging-accounts/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "platform": "slack",
  "account_id": "C1234567890",  # Channel ID
  "account_name": "General Channel",
  "channel_id": "C1234567890",
  "bot_token": "xoxb-your-bot-token"  # Optional if using global SLACK_BOT_TOKEN
}
```

#### 2. Send a Message

```bash
POST /messaging-accounts/send-message
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "platform": "slack",
  "account_id": "C1234567890",
  "channel_id": "C1234567890",
  "message": "Hello from Donna!"
}
```

#### 3. Setup Webhook (if using event subscriptions)

```bash
POST /messaging-accounts/setup-webhook?platform=slack&account_id=C1234567890
Authorization: Bearer YOUR_JWT_TOKEN
```

### Option B: Direct Bot Usage

If you've set `SLACK_BOT_TOKEN` in your `.env`, you can use the bot directly:

1. Invite the bot to a channel: `/invite @YourBotName`
2. Send messages to the channel - the bot can respond (if webhooks are configured)
3. Or mention the bot: `@YourBotName what's on my calendar?`

---

## Testing the Integration

### Quick Test Script (Recommended)

We've included a test script to verify your Slack integration:

```bash
cd backend
python test_slack.py
```

This will:
1. ✅ Verify your bot token is valid
2. ✅ Test listing channels (if you have the scope)
3. ⚠️  Show instructions for testing message sending

To test sending a message, provide a channel ID:

```bash
python test_slack.py C1234567890
```

**How to get a Channel ID:**
1. Open Slack in your browser
2. Go to the channel you want to test
3. Right-click the channel name → **"View channel details"**
4. Scroll down to find the **Channel ID** (starts with `C` for public channels)

### Test Bot Token Manually

You can also test your bot token directly with curl:

```bash
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer xoxb-your-bot-token" \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "ok": true,
  "url": "https://your-workspace.slack.com/",
  "team": "Your Team Name",
  "user": "your-bot-name",
  "team_id": "T1234567890",
  "user_id": "U1234567890"
}
```

### Test via Donna API

Once your backend is running, you can test sending messages via the API:

**1. First, add a messaging account:**
```bash
POST http://localhost:8000/messaging-accounts/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "platform": "slack",
  "account_id": "C1234567890",
  "account_name": "Test Channel",
  "channel_id": "C1234567890",
  "bot_token": "xoxb-your-token"  # Optional if using SLACK_BOT_TOKEN from .env
}
```

**2. Then send a test message:**
```bash
POST http://localhost:8000/messaging-accounts/send-message
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "platform": "slack",
  "account_id": "C1234567890",
  "channel_id": "C1234567890",
  "message": "🧪 Test message from Donna!"
}
```

### Test Webhook URL

If using webhooks, Slack will automatically verify your URL when you save it in Event Subscriptions. You should see a success message.

**Webhook Setup Checklist:**
1. ✅ Event Subscriptions enabled
2. ✅ Request URL set: `https://your-domain.com/messaging-accounts/webhook/slack`
3. ✅ Bot events subscribed: `message.channels`, `message.groups`, `message.im`, `message.mpim`
4. ✅ `SLACK_SIGNING_SECRET` added to `.env`
5. ✅ URL verification challenge passed (Slack will test this automatically)

**Testing the Webhook:**
1. Make sure your backend server is running
2. Save the webhook URL in Slack's Event Subscriptions
3. Slack will send a verification challenge - the endpoint should respond with the challenge token
4. Once verified, send a message to a channel where the bot is invited
5. Donna should process the message and respond!

---

## Troubleshooting

### Bot doesn't respond to messages

1. **Check Event Subscriptions**: Make sure events are enabled and your webhook URL is verified
2. **Check Bot is in Channel**: The bot must be invited to the channel
3. **Check Scopes**: Ensure `chat:write` and message history scopes are added
4. **Check Webhook URL**: Make sure it's publicly accessible (use ngrok for local dev)

### "Invalid token" error

- Verify your `SLACK_BOT_TOKEN` starts with `xoxb-`
- Make sure you copied the **Bot User OAuth Token**, not the App-Level Token
- Reinstall the app if the token was revoked

### Webhook verification fails

- Ensure your server is running and accessible
- Check that the webhook endpoint is at `/messaging-accounts/webhook/slack`
- For local development, use ngrok: `ngrok http 8000`
- Make sure your server returns 200 OK for the verification challenge

### Bot can't send messages

- Check that `chat:write` scope is added
- Verify the bot is invited to the channel
- Check channel permissions (some channels restrict bot messages)

---

## Security Notes

1. **Never commit tokens to git** - Always use `.env` file
2. **Use environment variables** - Don't hardcode tokens in code
3. **Rotate tokens** - If a token is exposed, regenerate it in Slack
4. **Limit scopes** - Only request the scopes you actually need
5. **Use signing secret** - Always verify webhook requests using `SLACK_SIGNING_SECRET`

---

## Next Steps

Once Slack is set up, you can:
- Send messages to Slack channels via Donna
- Receive messages from Slack and process them with Donna's AI
- Integrate Slack into your workflow for calendar, email, and reminders

For more information, see the [Slack API documentation](https://api.slack.com/).

