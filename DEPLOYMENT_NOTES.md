# Deployment Notes - User Login + Onboarding Implementation

## Summary
This deployment adds user login persistence, onboarding flow, and user history tracking.

## What's Changed

### Backend Changes
1. **New Migration**: `71429927dc58_add_onboarding_and_history.py`
   - Adds `onboarding_complete` field to users table
   - Adds `slack_access_token` field to users table  
   - Changes token fields to TEXT type
   - Creates new `user_history` table

2. **New Models**: 
   - `UserHistory` model for storing user interaction history

3. **New Routes**:
   - `POST /onboarding/complete` - Mark onboarding as complete
   - `GET /onboarding/status` - Check onboarding status
   - `GET /history` - Get user history
   - `POST /history` - Create history entry

4. **Updated Routes**:
   - `POST /auth/login` - Now returns user info with token
   - `POST /auth/register` - Now returns user info with token
   - `GET /auth/me` - Now includes `onboarding_complete` field

5. **Bug Fix**: Fixed timezone issue in `MessagingAccount` model (datetime.utcnow instead of datetime.now(timezone.utc))

### Frontend Changes (Desktop & Mobile)
- New Onboarding screens
- Updated login flows to check onboarding status
- Token persistence improvements

## Deployment Steps

### 1. Commit All Changes
```bash
git add .
git commit -m "Add user login persistence, onboarding flow, and user history"
git push origin main
```

### 2. Auto-Deployment
If using Render/Railway with auto-deploy:
- Push to main branch will trigger deployment
- Migrations run automatically via `entrypoint.sh`
- No manual steps needed!

### 3. Manual Deployment (if needed)
The `entrypoint.sh` script automatically runs:
```bash
alembic upgrade head
```

So migrations will run on container startup.

### 4. Verify Deployment
1. Check health endpoint: `GET /health`
2. Test login endpoint: `POST /auth/login`
3. Check that migrations ran: Check logs for "Running database migrations..."

## Database Migration
The migration will:
- Add `onboarding_complete` column (defaults to False for existing users)
- Add `slack_access_token` column
- Create `user_history` table
- Convert token columns to TEXT type

**No data loss** - all changes are additive.

## Rollback Plan
If issues occur, you can rollback by:
```bash
# In production database
alembic downgrade -1
```

Then redeploy previous code version.

## Testing Checklist
- [ ] Login works
- [ ] New users see onboarding screen
- [ ] Onboarding completion works
- [ ] History endpoints work
- [ ] Existing users still work (onboarding_complete defaults to False)
- [ ] Slack integration timezone fix works

