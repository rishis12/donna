# Slack OAuth Setup Guide

## Quick Setup Steps

### 1. Create Slack App
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: `Donna AI Assistant`
4. Select your workspace
5. Click "Create App"

### 2. Configure OAuth
1. Go to **OAuth & Permissions** (left sidebar)
2. Scroll to **Redirect URLs** → Add:
   ```
   http://localhost:8000/auth/slack/callback
   ```
3. Scroll to **Scopes** → **Bot Token Scopes** → Add:
   - `chat:write`
   - `channels:read`
   - `groups:read`
   - `im:read`
   - `mpim:read`
   - `channels:history`
   - `groups:history`
   - `im:history`
   - `mpim:history`
   - `users:read`
   - `app_mentions:read`
4. Scroll to top → Click **"Install to Workspace"**
5. Copy your credentials:
   - **Client ID** (under "App Credentials")
   - **Client Secret** (click "Show" to reveal)

### 3. Add to .env File
Open `backend/.env` and add:

```env
# Slack OAuth
SLACK_CLIENT_ID=your-client-id-here
SLACK_CLIENT_SECRET=your-client-secret-here
SLACK_REDIRECT_URI=http://localhost:8000/auth/slack/callback
```

**Replace `your-client-id-here` and `your-client-secret-here` with your actual values!**

### 4. Restart Backend
After adding the credentials, restart your backend server.

## Verification
After setup, try connecting Slack in the app settings. It should open the Slack authorization page.


