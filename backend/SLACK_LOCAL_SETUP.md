# Slack OAuth Setup for Local Development

Since Slack requires HTTPS for redirect URIs, you need to use a tunneling service like ngrok for local development.

## Option 1: Using ngrok (Recommended)

### Step 1: Install ngrok
Download from https://ngrok.com/download or install via package manager:
```bash
# Windows (via Chocolatey)
choco install ngrok

# Or download from https://ngrok.com/download
```

### Step 2: Start ngrok tunnel
```bash
ngrok http 8000
```

This will give you a URL like: `https://abc123.ngrok-free.app`

### Step 3: Update your .env file
```env
BASE_URL=https://abc123.ngrok-free.app
SLACK_REDIRECT_URI=https://abc123.ngrok-free.app/auth/slack/callback
```

**Important:** Replace `abc123.ngrok-free.app` with your actual ngrok URL!

### Step 4: Update Slack App Settings
1. Go to https://api.slack.com/apps
2. Select your app
3. Go to **OAuth & Permissions**
4. Under **Redirect URLs**, add:
   ```
   https://abc123.ngrok-free.app/auth/slack/callback
   ```
5. Click **Save URLs**

### Step 5: Restart your backend
After updating .env, restart your backend server.

## Option 2: Using localhost.run (Alternative)

If you prefer not to install ngrok:

```bash
ssh -R 80:localhost:8000 serveo.net
```

This will give you an HTTPS URL you can use.

## Important Notes

- **ngrok URLs change** each time you restart ngrok (unless you have a paid plan)
- You'll need to update both your `.env` file and Slack app settings when the URL changes
- For production, use your actual domain with HTTPS

## Quick Test

After setup, verify:
1. Your backend is running on port 8000
2. ngrok is running and forwarding to localhost:8000
3. Your .env has the ngrok HTTPS URL
4. Slack app has the same HTTPS URL configured
5. Try connecting Slack in your app


