# Scalable Deployment Architecture

## Current State vs. Scalable State

### ✅ What Already Works for Scale

1. **Google OAuth (Gmail/Calendar)**
   - ✅ **One-time setup**: You create ONE OAuth app in Google Cloud Console
   - ✅ **Users just authenticate**: Users click "Connect Google" → authenticate → done
   - ✅ **Multi-tenant**: One app registration serves all users
   - ✅ **No user setup required**

2. **Microsoft OAuth (Outlook/Teams/Calendar)**
   - ✅ **One-time setup**: You create ONE app registration in Azure Portal
   - ✅ **Users just authenticate**: Users click "Connect Microsoft" → authenticate → done
   - ✅ **Multi-tenant**: One app registration serves all users
   - ✅ **No user setup required**

### ❌ What Needs to Change for Scale

1. **Slack Integration**
   - ❌ **Current**: Users must create their own Slack app, configure webhooks, set up event subscriptions
   - ✅ **Should be**: Use Slack OAuth (like Google/Microsoft) - users just install your app to their workspace

2. **OAuth Redirect URIs**
   - ❌ **Current**: Hardcoded to `localhost:8000`
   - ✅ **Should be**: Dynamic based on environment (dev/staging/prod)

---

## Recommended Architecture for Scale

### 1. OAuth Apps (One-Time Setup by You)

You create **one** OAuth app registration for each platform:

- **Google Cloud Console**: One OAuth client
- **Azure Portal**: One app registration
- **Slack API**: One Slack app (for OAuth, not webhooks)

**All users share these app registrations** - they just authenticate with their own accounts.

### 2. User Experience (Zero Setup)

Users simply:
1. Sign up/login to your app
2. Click "Connect Google" → OAuth flow → Done
3. Click "Connect Microsoft" → OAuth flow → Done
4. Click "Connect Slack" → Install app to workspace → Done

**No webhook configuration, no app creation, no technical setup.**

### 3. Slack: Switch from Webhooks to OAuth

**Current Problem:**
- Users must create their own Slack app
- Users must configure webhook URLs
- Users must set up event subscriptions
- Not scalable

**Solution: OAuth Installation Flow**

Instead of webhooks, use Slack's OAuth installation:
1. You create ONE Slack app in Slack API
2. Users click "Connect Slack" in your app
3. They're redirected to Slack to install your app to their workspace
4. Slack redirects back with an access token
5. Your app uses the token to access their Slack data
6. For real-time messages, use Slack's Socket Mode or Events API with a single webhook URL

**Benefits:**
- ✅ Users just click "Install" - no technical setup
- ✅ One webhook URL for all users (your server)
- ✅ Proper OAuth flow like Google/Microsoft

---

## Implementation Changes Needed

### 1. Update OAuth Redirect URIs

**Current:** Hardcoded `localhost:8000`

**Change to:** Environment-based redirects

```python
# backend/app/core/config.py
class Settings:
    def __init__(self):
        # ... existing code ...
        
        # OAuth redirects - environment-based
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        self.google_redirect_uri = f"{base_url}/auth/google/callback"
        self.microsoft_redirect_uri = f"{base_url}/auth/microsoft/callback"
        self.slack_redirect_uri = f"{base_url}/auth/slack/callback"
```

**Environment Variables:**
```env
# Development
BASE_URL=http://localhost:8000

# Production
BASE_URL=https://api.yourdomain.com
```

**Update OAuth App Registrations:**
- Google Cloud Console: Add production redirect URI
- Azure Portal: Add production redirect URI
- Slack App: Add production redirect URI

### 2. Implement Slack OAuth Flow

**Current:** Manual webhook setup per user

**New:** OAuth installation flow

```python
# backend/app/api/routes/auth.py - Add Slack OAuth
@router.get("/slack")
async def slack_oauth_start():
    """Start Slack OAuth flow."""
    # Redirect to Slack OAuth URL
    # Similar to Google/Microsoft flows
    pass

@router.get("/slack/callback")
async def slack_oauth_callback(code: str, state: str):
    """Handle Slack OAuth callback."""
    # Exchange code for token
    # Store token for user
    # Similar to Google/Microsoft flows
    pass
```

**Slack App Configuration:**
1. Create ONE Slack app at https://api.slack.com/apps
2. Configure OAuth & Permissions:
   - Redirect URL: `https://api.yourdomain.com/auth/slack/callback`
   - Scopes: `channels:read`, `chat:write`, `users:read`, etc.
3. Configure Event Subscriptions:
   - Request URL: `https://api.yourdomain.com/messaging-accounts/webhook/slack`
   - Subscribe to: `message.channels`, `message.groups`, `message.im`
4. Store `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` in environment

**User Flow:**
1. User clicks "Connect Slack" in your app
2. Redirected to Slack: `https://slack.com/oauth/v2/authorize?...`
3. User approves installation
4. Slack redirects to your callback with code
5. Your backend exchanges code for access token
6. Store token (encrypted) in database
7. Done - user can now use Slack

### 3. Update Documentation

Remove user-facing setup instructions for:
- Creating OAuth apps
- Configuring webhooks
- Setting up event subscriptions

Replace with:
- "Click Connect → Authenticate → Done"

---

## Deployment Checklist

### Pre-Deployment (One-Time Setup)

- [ ] Create Google OAuth app (if not done)
  - Add production redirect URI: `https://api.yourdomain.com/auth/google/callback`
  - Add staging redirect URI if needed

- [ ] Create Microsoft app registration (if not done)
  - Add production redirect URI: `https://api.yourdomain.com/auth/microsoft/callback`
  - Add staging redirect URI if needed

- [ ] Create Slack app (NEW - replace webhook approach)
  - Configure OAuth redirect: `https://api.yourdomain.com/auth/slack/callback`
  - Configure Event Subscriptions webhook: `https://api.yourdomain.com/messaging-accounts/webhook/slack`
  - Add required scopes
  - Store `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`

### Environment Variables

```env
# Base URL (for OAuth redirects)
BASE_URL=https://api.yourdomain.com

# Google OAuth (already have)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Microsoft OAuth (already have)
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...

# Slack OAuth (NEW - replace webhook tokens)
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
SLACK_SIGNING_SECRET=...  # For webhook verification (one webhook for all users)
```

### Code Changes

- [ ] Update `Settings` class to use `BASE_URL` for redirect URIs
- [ ] Implement Slack OAuth flow (similar to Google/Microsoft)
- [ ] Update Slack webhook handler to work with OAuth tokens
- [ ] Remove user-facing webhook setup endpoints
- [ ] Update frontend to show "Connect Slack" button (OAuth flow)

---

## User Experience Comparison

### Before (Current - Not Scalable)

**Slack Setup:**
1. User goes to Slack API website
2. Creates a new Slack app
3. Configures OAuth scopes
4. Sets up event subscriptions
5. Configures webhook URL
6. Gets bot token
7. Manually adds token to your app
8. Invites bot to channels

**Time:** 15-30 minutes, technical knowledge required

### After (Scalable)

**Slack Setup:**
1. User clicks "Connect Slack" in your app
2. Approves installation in Slack
3. Done

**Time:** 30 seconds, no technical knowledge required

---

## Security Considerations

### OAuth Apps (Your Setup)

- ✅ One app registration per platform (you manage)
- ✅ Client secrets stored securely (environment variables)
- ✅ Redirect URIs whitelisted (only your domains)

### User Tokens

- ✅ Stored encrypted in database
- ✅ Per-user tokens (users authenticate with their accounts)
- ✅ Refresh tokens for automatic renewal
- ✅ Token rotation support

### Webhooks (Slack)

- ✅ Single webhook URL (your server)
- ✅ Signature verification (prevents spoofing)
- ✅ Route to correct user based on workspace/team ID

---

## Migration Path

If you have existing users with manual Slack setups:

1. **Phase 1**: Implement OAuth flow alongside webhook flow
2. **Phase 2**: Show migration prompt to existing users
3. **Phase 3**: Deprecate manual webhook setup
4. **Phase 4**: Remove webhook setup code

---

## Summary

**What users do:**
- ✅ Click "Connect" buttons
- ✅ Authenticate with their accounts
- ✅ Done

**What you do (one-time):**
- ✅ Create OAuth apps in Google/Azure/Slack
- ✅ Configure redirect URIs
- ✅ Store client secrets securely

**No user setup required!** 🎉


