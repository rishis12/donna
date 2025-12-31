# Setting Up Email and Teams Access

## Overview
You need to create OAuth app registrations in Google Cloud Console and Azure Portal. Once set up, users authenticate with their accounts, and OAuth tokens provide API access (no separate API keys needed).

---

## 1. Google (Gmail) Setup

### Creating Google OAuth App (First Time)

1. **Go to Google Cloud Console**: https://console.cloud.google.com/

2. **Create a Project** (if you don't have one):
   - Click the project dropdown at the top
   - Click "New Project"
   - Name: "Donna AI Assistant" (or whatever)
   - Click "Create"

3. **Enable Gmail API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

4. **Configure OAuth Consent Screen**:
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "External" (unless you have a Google Workspace)
   - Fill in required fields:
     - App name: "Donna AI Assistant"
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"
   - Add scopes: Click "Add or Remove Scopes"
     - Add: `https://www.googleapis.com/auth/gmail.modify`
     - Add: `https://www.googleapis.com/auth/calendar`
     - Add: `https://www.googleapis.com/auth/userinfo.email`
     - Add: `https://www.googleapis.com/auth/userinfo.profile`
   - Click "Update" then "Save and Continue"
   - Add test users if in testing mode (your email)
   - Click "Save and Continue" → "Back to Dashboard"

5. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "+ Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "Donna Web Client"
   - **Authorized redirect URIs**: 
     - `http://localhost:8000/auth/google/callback`
   - Click "Create"
   - **Copy the Client ID and Client Secret**
   - Add to your `backend/.env` file:
     ```
     GOOGLE_CLIENT_ID=your-client-id-here
     GOOGLE_CLIENT_SECRET=your-client-secret-here
     ```

### Scopes Already Configured in Code:
```python
"https://www.googleapis.com/auth/gmail.modify"  # Read, compose, and send emails
```

**No additional API keys needed** - OAuth tokens provide access!

---

## 2. Microsoft (Outlook + Teams) Setup

### ⚠️ Important: Which Account to Use?

**Register the app on your PERSONAL Microsoft account**, not your school account. Here's why:

- ✅ **App Registration Account** (Personal): This is where you register the app - you'll always have access
- ✅ **User Authentication**: Users authenticate with THEIR accounts (school/work/personal) - separate from app registration
- ✅ **Access to School Data**: You can still access your school email/Teams when you authenticate with your school account
- ❌ **Risk if using school account**: If you lose access to the school account, you lose access to manage the app

**Bottom line**: Register on personal account, but users can authenticate with any account (including school).

### Creating the App Registration (First Time)

1. **Go to Azure Portal**: https://portal.azure.com/
   - **Sign in with your PERSONAL Microsoft account** (not school)

2. **Create a New App Registration**:
   - Click "Azure Active Directory" (or search for it)
   - Go to "App registrations" in the left menu
   - Click "+ New registration"
   - **Name**: "Donna AI Assistant" (or whatever you want)
   - **Supported account types**: Select "Accounts in any organizational directory and personal Microsoft accounts"
   - **Redirect URI**: 
     - Platform: "Web"
     - URI: `http://localhost:8000/auth/microsoft/callback`
   - Click "Register"

3. **Save Your Credentials**:
   - After registration, you'll see "Overview"
   - Copy the **Application (client) ID** → This is your `MICROSOFT_CLIENT_ID`
   - Go to "Certificates & secrets" → "New client secret"
   - Description: "Donna Secret" (or whatever)
   - Expires: Choose duration (24 months recommended)
   - Click "Add"
   - **IMMEDIATELY copy the Value** (you can't see it again!) → This is your `MICROSOFT_CLIENT_SECRET`
   - Add these to your `backend/.env` file:
     ```
     MICROSOFT_CLIENT_ID=your-client-id-here
     MICROSOFT_CLIENT_SECRET=your-client-secret-here
     ```

4. **Configure Redirect URIs**:
   - Go to "Authentication" in left menu
   - Under "Redirect URIs", make sure you have:
     - `http://localhost:8000/auth/microsoft/callback`
   - Click "Save"

### Adding API Permissions

1. **Navigate to your App Registration**:
   - Go to "Azure Active Directory" → "App registrations"
   - Find your app (the one you just created)

2. **Add API Permissions**:
   - Click "API permissions" in the left menu
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Select "Delegated permissions"
   - Add these permissions:
     - ✅ `User.Read` (Read user profile)
     - ✅ `Calendars.ReadWrite` (Read and write calendars)
     - ✅ `Mail.Send` (Send mail)
     - ✅ `Mail.Read` (Read user mail)
     - ✅ `Chat.Read` (Read user chat messages)
     - ✅ `ChatMessage.Read` (Read chat messages)
   - Click "Add permissions"

3. **Grant Admin Consent** (REQUIRED for school/work accounts):
   - ⚠️ **Important**: If you want to access school/work account data, you need admin consent
   - Click "Grant admin consent for [Your Organization]" (if you have admin rights)
   - **OR** ask your IT admin to grant consent for your organization
   - **OR** users can grant individual consent (but some permissions require admin)
   - For personal accounts, individual consent works fine
   - You should see green checkmarks after consent is granted

### Scopes Already Configured in Code:
```python
"Mail.Read"        # For reading Outlook emails
"Chat.Read"        # For reading Teams chats
"ChatMessage.Read" # For reading Teams messages
```

**No additional API keys needed** - OAuth tokens provide access!

---

## 3. How It Works

### OAuth Flow
1. User clicks "Connect Google" or "Connect Microsoft" in your app
2. They're redirected to Google/Microsoft login
3. They authenticate with **their account** (school/work/personal - doesn't matter which)
4. They grant permissions for the app to access their data
5. Your backend receives an **access token** and **refresh token**
6. These tokens are used to make API calls to Gmail/Outlook/Teams
7. **No separate API keys needed** - the tokens ARE the authentication

### Key Points:
- **App Registration Account** ≠ **User Authentication Account**
  - App registered on personal account = permanent access to manage app
  - Users authenticate with their own accounts = access to their data
  - You can access school data even if app is registered on personal account

### Token Storage
- Tokens are stored encrypted in your database
- Refresh tokens are used to get new access tokens when they expire
- The placeholder functions will use these tokens once you implement them

---

## 4. Testing

### After Setup:
1. **Restart your backend** to load new credentials from `.env`
2. **Disconnect and reconnect** Google/Microsoft accounts in your app's Settings
3. Users will see permission prompts like:
   - "Donna AI Assistant wants to read your emails"
   - "Donna AI Assistant wants to read your Teams messages"
4. Grant permissions
5. Once granted, the placeholder functions can be replaced with real API calls

### For School/Work Accounts:
- You may need **admin consent** before individual users can grant permissions
- Contact your IT admin if consent fails
- Admin consent is one-time per organization

---

## 5. Implementation Checklist

### Google Setup
- [ ] Create Google Cloud Project
- [ ] Enable Gmail API
- [ ] Configure OAuth consent screen
- [ ] Create OAuth 2.0 Client ID
- [ ] Add redirect URI: `http://localhost:8000/auth/google/callback`
- [ ] Save `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `backend/.env`

### Microsoft Setup
- [ ] Create Azure App Registration (**use PERSONAL account**)
- [ ] Add redirect URI: `http://localhost:8000/auth/microsoft/callback`
- [ ] Create client secret
- [ ] Add API Permissions: `Mail.Read`, `Chat.Read`, `ChatMessage.Read`, `User.Read`, `Calendars.ReadWrite`, `Mail.Send`
- [ ] Grant admin consent (if accessing school/work accounts - ask IT admin if needed)
- [ ] Save `MICROSOFT_CLIENT_ID` and `MICROSOFT_CLIENT_SECRET` to `backend/.env`

### Testing
- [ ] Restart backend server
- [ ] Test by connecting Google account
- [ ] Test by connecting Microsoft account (try with school account)
- [ ] Verify permissions are granted
- [ ] Update placeholder functions with real API calls (when ready)
- [ ] Verify email/Teams access works

---

## 6. Important Notes

### Account Separation:
- **App Registration Account** ≠ **User Account**: 
  - Register the app on your personal account (for permanent access)
  - Users authenticate with their own accounts (school/personal/work)
  - You can access school data even if app is registered on personal account

### Admin Consent:
- **Required for organizations**: School/work accounts often need admin consent
- Contact IT admin if you can't grant consent yourself
- Personal accounts don't need admin consent
- Admin consent is one-time per organization

### Security:
- Never commit `.env` file with real credentials to git
- Client secrets should be kept secure
- OAuth tokens are encrypted in database

### Other Notes:
- **No API keys needed** - OAuth tokens provide all access
- **Users must re-authenticate** after you add new scopes
- The placeholder functions return empty arrays until you implement them
- Once implemented, the LLM summaries will work automatically!

---

## 7. Slack (Future)

When you're ready to add Slack:
1. Go to https://api.slack.com/apps
2. Create a new app
3. Configure OAuth scopes:
   - `channels:read`
   - `groups:read`
   - `im:read`
   - `mpim:read`
   - `chat:write` (if you want to send messages)
4. Get `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`
5. Add to `.env` and implement OAuth flow (similar to Google/Microsoft)
