# Fix OAuth Social Login on Render

## Problem
Social login (Google/Microsoft) is using `localhost` URLs instead of your Render URL.

## Solution: Update Environment Variables on Render

### Step 1: Update BASE_URL in Render

1. Go to your [Render Dashboard](https://dashboard.render.com)
2. Click on your backend service (`donna-backend`)
3. Go to **Environment** tab
4. Add/Update the `BASE_URL` variable:
   ```
   BASE_URL=https://donna-backend-oc7v.onrender.com
   ```
5. Click **Save Changes**
6. **Redeploy** your service (Render will auto-redeploy after saving)

### Step 2: Update OAuth Redirect URIs

#### For Google OAuth:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** → **Credentials**
3. Click on your OAuth 2.0 Client ID
4. Under **Authorized redirect URIs**, add:
   ```
   https://donna-backend-oc7v.onrender.com/auth/google/callback
   ```
5. **Remove** any localhost redirect URIs (or keep them for local testing)
6. Click **Save**

#### For Microsoft OAuth:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click on your app
4. Go to **Authentication**
5. Under **Redirect URIs**, add:
   ```
   https://donna-backend-oc7v.onrender.com/auth/microsoft/callback
   ```
6. Click **Save**

### Step 3: Update Environment Variables in Render (Optional but Recommended)

In your Render service Environment tab, you can also explicitly set:

```
GOOGLE_REDIRECT_URI=https://donna-backend-oc7v.onrender.com/auth/google/callback
MICROSOFT_REDIRECT_URI=https://donna-backend-oc7v.onrender.com/auth/microsoft/callback
```

However, if `BASE_URL` is set correctly, these will be generated automatically.

### Step 4: Verify

1. After Render redeploys, test the OAuth flow
2. When you click "Login with Google" or "Login with Microsoft":
   - It should redirect to Google/Microsoft login page
   - After login, it should redirect back to `https://donna-backend-oc7v.onrender.com/auth/[provider]/callback`
   - You should see a page with a token to copy

## Quick Checklist

- [ ] `BASE_URL` set to `https://donna-backend-oc7v.onrender.com` in Render
- [ ] Google redirect URI added: `https://donna-backend-oc7v.onrender.com/auth/google/callback`
- [ ] Microsoft redirect URI added: `https://donna-backend-oc7v.onrender.com/auth/microsoft/callback`
- [ ] Render service redeployed after environment changes
- [ ] Test OAuth login flow

## Troubleshooting

**Still seeing localhost?**
- Make sure you redeployed after changing environment variables
- Check Render logs to see what BASE_URL is being used
- Clear your browser cache

**OAuth redirect fails?**
- Verify redirect URIs match EXACTLY (including https://)
- Check Google/Microsoft console for any errors
- Look at Render logs for callback errors

