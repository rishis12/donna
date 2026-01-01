# Outlook & Teams Integration Setup Guide

This guide walks you through setting up Microsoft Outlook (email) and Teams integration for Donna. Once configured, users can connect their Microsoft accounts with a single click - no technical setup required on their end!

---

## Overview

**What you need to do (one-time setup):**
1. Create an Azure App Registration
2. Configure API permissions for Outlook and Teams
3. Add credentials to your `.env` file

**What users do:**
1. Click "Connect Microsoft" in your app
2. Sign in with their Microsoft account
3. Grant permissions
4. Done! ✅

---

## Step-by-Step Setup

### Step 1: Create Azure App Registration

1. **Go to Azure Portal**
   - Visit: https://portal.azure.com/
   - **⚠️ Important**: Sign in with your **PERSONAL Microsoft account** (not a school/work account)
   - This ensures you maintain access to manage the app registration

2. **Navigate to App Registrations**
   - Search for "Azure Active Directory" in the top search bar
   - Click on "Azure Active Directory" in the results
   - In the left menu, click **"App registrations"**
   - Click **"+ New registration"**

3. **Register Your Application**
   - **Name**: `Donna AI Assistant` (or your preferred name)
   - **Supported account types**: 
     - Select: **"Accounts in any organizational directory and personal Microsoft accounts"**
     - This allows users to sign in with any Microsoft account (personal, work, or school)
   - **Redirect URI**:
     - Platform: **"Web"**
     - URI: 
       - For development: `http://localhost:8000/auth/microsoft/callback`
       - For production: `https://yourdomain.com/auth/microsoft/callback`
   - Click **"Register"**

4. **Save Your Application (Client) ID**
   - After registration, you'll see the **Overview** page
   - Copy the **Application (client) ID** - you'll need this for your `.env` file
   - This is your `MICROSOFT_CLIENT_ID`

---

### Step 2: Create Client Secret

1. **Navigate to Certificates & Secrets**
   - In the left menu, click **"Certificates & secrets"**
   - Under "Client secrets", click **"+ New client secret"**

2. **Create the Secret**
   - **Description**: `Donna Secret` (or any name you prefer)
   - **Expires**: Choose duration (24 months recommended)
   - Click **"Add"**

3. **⚠️ CRITICAL: Copy the Secret Value Immediately**
   - After creating, you'll see the secret in the list
   - **Copy the "Value" column** (not the Secret ID)
   - **You can only see this once!** If you miss it, you'll need to create a new secret
   - This is your `MICROSOFT_CLIENT_SECRET`

---

### Step 3: Configure Redirect URIs (For Production)

If you're deploying to production, add your production redirect URI:

1. **Go to Authentication**
   - In the left menu, click **"Authentication"**
   - Under "Redirect URIs", click **"+ Add a platform"** if needed
   - Add your production URI: `https://yourdomain.com/auth/microsoft/callback`
   - Click **"Save"**

---

### Step 4: Add API Permissions

1. **Navigate to API Permissions**
   - In the left menu, click **"API permissions"**

2. **Add Microsoft Graph Permissions**
   - Click **"+ Add a permission"**
   - Select **"Microsoft Graph"**
   - Select **"Delegated permissions"** (not Application permissions)
   
3. **Add the Following Permissions**
   
   **For Outlook (Email):**
   - ✅ `Mail.Read` - Read user mail
   - ✅ `Mail.Send` - Send mail as the user
   
   **For Calendar:**
   - ✅ `Calendars.ReadWrite` - Read and write user calendars
   
   **For Teams:**
   - ✅ `Chat.Read` - Read user chat messages
   - ✅ `ChatMessage.Read` - Read chat messages
   - ✅ `ChatMessage.Send` - Send chat messages
   
   **For User Info:**
   - ✅ `User.Read` - Read user profile (usually added by default)
   
   - Click **"Add permissions"** after selecting all

4. **Grant Admin Consent (Important for Organizations)**
   
   **For Personal Accounts:**
   - ✅ Individual consent works fine - users will grant permissions when they connect
   
   **For Work/School Accounts:**
   - ⚠️ **Admin consent may be required** before users can grant permissions
   - If you have admin rights: Click **"Grant admin consent for [Your Organization]"**
   - If you don't have admin rights: 
     - Contact your IT administrator
     - Provide them with your Application (client) ID
     - Ask them to grant admin consent for the permissions
   - After consent, you should see green checkmarks ✅

---

### Step 5: Add Credentials to Your .env File

1. **Open your `.env` file**
   - Located in: `backend/.env`

2. **Add the Microsoft credentials:**
   ```env
   # Microsoft OAuth (Outlook & Teams)
   MICROSOFT_CLIENT_ID=your-application-client-id-here
   MICROSOFT_CLIENT_SECRET=your-client-secret-value-here
   
   # Base URL (for redirect URIs)
   # Development:
   BASE_URL=http://localhost:8000
   
   # Production (when deploying):
   # BASE_URL=https://yourdomain.com
   ```

3. **Replace the placeholder values** with:
   - `MICROSOFT_CLIENT_ID`: The Application (client) ID from Step 1
   - `MICROSOFT_CLIENT_SECRET`: The secret value from Step 2 (the one you copied immediately)

---

### Step 6: Restart Your Backend Server

1. **Stop your backend server** (if running)
2. **Start it again** to load the new environment variables
   ```bash
   cd backend
   # Your usual startup command (e.g., uvicorn, python -m app.main, etc.)
   ```

---

## Testing the Integration

### Test Connection Flow

1. **Start your backend server** (with the new credentials)
2. **Open your app** (desktop or mobile)
3. **Navigate to Settings** (or wherever your "Connect" buttons are)
4. **Click "Connect Microsoft"** or "Connect Outlook"
5. **You should be redirected to Microsoft login**
6. **Sign in with your Microsoft account** (can be personal, work, or school)
7. **Review and grant permissions**
8. **You should be redirected back** to your app
9. **Connection successful!** ✅

### Verify Permissions

After connecting, you can verify it's working:

1. **Check your database** - The user should have `microsoft_access_token` and `microsoft_refresh_token` stored (encrypted)
2. **Try using features** that require Microsoft access:
   - Reading emails
   - Sending emails
   - Viewing calendar events
   - Reading Teams messages

---

## Important Notes

### Account Types

**App Registration Account vs. User Authentication Account:**
- ✅ **Register the app** on your **personal Microsoft account** (ensures permanent access)
- ✅ **Users authenticate** with **their own accounts** (personal, work, or school)
- ✅ Users can access their **school/work data** even though the app is registered on your personal account
- ❌ **Don't register on school/work account** - you might lose access if you leave

### Admin Consent

**When is admin consent required?**
- Some organizations require admin consent before users can grant permissions
- Personal Microsoft accounts usually don't require admin consent
- Work/school accounts may require it

**How to handle admin consent:**
- If you're an admin: Grant consent in Azure Portal (Step 4)
- If you're not an admin: Contact your IT administrator
- Admin consent is **one-time per organization** - after granted, all users in that organization can connect

### Security

- ✅ **Never commit `.env` file** to version control
- ✅ **Client secrets are sensitive** - keep them secure
- ✅ **Tokens are encrypted** in your database
- ✅ **Refresh tokens** automatically renew access tokens

### Production Deployment

**Before deploying to production:**

1. **Add production redirect URI** in Azure Portal (Step 3)
2. **Update `.env` file** with production `BASE_URL`:
   ```env
   BASE_URL=https://yourdomain.com
   ```
3. **Update redirect URIs** in Azure Portal to include your production URL
4. **Test the OAuth flow** with production URL

---

## Troubleshooting

### "Invalid client secret"
- Verify you copied the **Value** (not the Secret ID) from Azure Portal
- Check for extra spaces or characters in your `.env` file
- Make sure the secret hasn't expired (check expiration date in Azure Portal)

### "Redirect URI mismatch"
- Verify the redirect URI in Azure Portal matches exactly what's in your `.env` file
- Check that `BASE_URL` is set correctly in your `.env`
- For development: Should be `http://localhost:8000`
- For production: Should be `https://yourdomain.com`

### "Admin consent required"
- If users see this error, admin consent hasn't been granted for their organization
- Contact your IT administrator to grant admin consent
- Or test with a personal Microsoft account first (doesn't require admin consent)

### "Insufficient privileges"
- Verify all required permissions are added in Azure Portal (Step 4)
- Check that permissions are granted (green checkmarks ✅)
- Users may need to disconnect and reconnect after you add new permissions

### "Token refresh failed"
- Check that refresh tokens are being stored correctly
- Verify `MICROSOFT_CLIENT_SECRET` is correct
- Users may need to reconnect their account

---

## API Permissions Reference

Here's what each permission does:

| Permission | Purpose | Required For |
|------------|---------|--------------|
| `User.Read` | Read user profile information | User identification |
| `Mail.Read` | Read user's email messages | Outlook email access |
| `Mail.Send` | Send email on behalf of user | Sending emails |
| `Calendars.ReadWrite` | Read and create calendar events | Calendar integration |
| `Chat.Read` | Read user's Teams chats | Teams chat access |
| `ChatMessage.Read` | Read Teams messages | Teams messages |

---

## Summary Checklist

- [ ] Created Azure App Registration (with personal Microsoft account)
- [ ] Set redirect URI: `http://localhost:8000/auth/microsoft/callback`
- [ ] Created client secret and copied the value immediately
- [ ] Added API permissions (Mail.Read, Mail.Send, Calendars.ReadWrite, Chat.Read, ChatMessage.Read, ChatMessage.Send, User.Read)
- [ ] Granted admin consent (if required for your organization)
- [ ] Added `MICROSOFT_CLIENT_ID` to `.env` file
- [ ] Added `MICROSOFT_CLIENT_SECRET` to `.env` file
- [ ] Set `BASE_URL` in `.env` file
- [ ] Restarted backend server
- [ ] Tested connection flow
- [ ] Verified permissions work

---

## Next Steps

Once setup is complete:

1. **Users can connect** their Microsoft accounts with one click
2. **Your app can access** their Outlook emails and Teams messages
3. **Calendar integration** works automatically
4. **No user setup required** - it all happens through OAuth! 🎉

For production deployment, remember to:
- Add production redirect URI
- Update `BASE_URL` in production environment
- Test the flow with production URL

---

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all steps were completed correctly
3. Check Azure Portal for any error messages
4. Review your backend logs for detailed error information

