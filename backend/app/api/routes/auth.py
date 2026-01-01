from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas import UserCreate, UserLogin, Token, UserResponse
from typing import Optional
from ...core.database import get_db
from ...core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from ...models.user import User
from ...integrations import google_integration, microsoft_integration
from ...integrations.slack_integration import get_auth_url as get_slack_auth_url, exchange_code as exchange_slack_code, get_user_info as get_slack_user_info
from ...models.messaging_account import MessagingAccount
from ..deps import get_current_user
import json
import base64

router = APIRouter(prefix="/auth", tags=["auth"])

async def build_user_response(user: User, db: AsyncSession) -> UserResponse:
    """Helper function to build UserResponse from User model."""
    # Check if user has active Slack account
    slack_result = await db.execute(
        select(MessagingAccount)
        .where(MessagingAccount.user_id == user.id)
        .where(MessagingAccount.platform == "slack")
        .where(MessagingAccount.is_active == True)
    )
    slack_connected = slack_result.scalar_one_or_none() is not None
    
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        onboarding_complete=user.onboarding_complete or False,
        google_connected=bool(user.google_access_token),
        microsoft_connected=bool(user.microsoft_access_token),
        slack_connected=slack_connected
    )

# HTML template for OAuth callback - sends token back to desktop app
OAUTH_SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Success!</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(30, 41, 59, 0.8);
            border-radius: 1rem;
            border: 1px solid rgba(71, 85, 105, 0.3);
            max-width: 420px;
        }}
        h1 {{ color: #60a5fa; margin-bottom: 0.5rem; }}
        p {{ color: #94a3b8; margin: 0.5rem 0; }}
        .token {{ 
            font-family: monospace;
            background: #0f172a;
            padding: 1rem;
            border-radius: 0.5rem;
            word-break: break-all;
            margin: 1rem 0;
            font-size: 0.7rem;
            max-height: 100px;
            overflow-y: auto;
        }}
        button {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-size: 1rem;
            margin-top: 0.5rem;
        }}
        button:hover {{ background: #2563eb; }}
        .success {{ color: #34d399; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="success">{title}</h1>
        <p>{message}</p>
        {token_section}
    </div>
    <script>
        function copyToken() {{
            const token = document.getElementById('token');
            if (token) {{
                navigator.clipboard.writeText(token.textContent);
                alert('Token copied!');
            }}
        }}
    </script>
</body>
</html>
"""

TOKEN_SECTION = """
        <p style="font-size: 0.875rem; margin-top: 1rem;">Copy this token and paste it in the app:</p>
        <div class="token" id="token">{token}</div>
        <button onclick="copyToken()">Copy Token</button>
"""

CONNECT_SUCCESS_MESSAGE = "Service connected! You can close this window and return to the app."

def encode_state(data: dict) -> str:
    """Encode state data as base64 JSON."""
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def decode_state(state: str) -> dict:
    """Decode state data from base64 JSON."""
    try:
        return json.loads(base64.urlsafe_b64decode(state.encode()).decode())
    except:
        return {}

# Traditional email/password registration (optional)
@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    user_response = await build_user_response(user, db)
    return Token(access_token=token, user=user_response)

# Traditional email/password login (optional)
@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is OAuth-only
    if not user.hashed_password:
        raise HTTPException(
            status_code=401, 
            detail=f"This account uses {user.auth_provider or 'social'} sign-in. Please use that instead."
        )
    
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user.id)})
    user_response = await build_user_response(user, db)
    return Token(access_token=token, user=user_response)

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await build_user_response(user, db)

# ============================================
# Google OAuth
# ============================================

@router.get("/google")
async def google_auth(platform: str = Query(default="desktop")):
    """Start Google OAuth flow for login/signup."""
    state = encode_state({"action": "login", "platform": platform})
    return {"auth_url": google_integration.get_auth_url(state=state)}

@router.get("/google/connect")
async def google_connect(user: User = Depends(get_current_user)):
    """For already logged-in users who want to connect Google."""
    # Include user ID in state so callback knows to update this user
    state = encode_state({"action": "connect", "user_id": str(user.id)})
    return {"auth_url": google_integration.get_auth_url(state=state)}

@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Google OAuth callback - handles both login and connect flows."""
    try:
        state_data = decode_state(state) if state else {}
        action = state_data.get("action", "login")
        platform = state_data.get("platform", "desktop")
        
        # Exchange code for tokens
        tokens = await google_integration.exchange_code(code)
        
        if action == "connect" and state_data.get("user_id"):
            # Connect flow - update existing user
            user_id = state_data["user_id"]
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise Exception("User not found")
            
            user.google_access_token = tokens["access_token"]
            if tokens.get("refresh_token"):
                user.google_refresh_token = tokens["refresh_token"]
            
            await db.commit()
            
            # For mobile, redirect back to app
            if platform == "mobile":
                return RedirectResponse(url="donna://auth/callback?status=connected&provider=google")
            
            return HTMLResponse(content=OAUTH_SUCCESS_HTML.format(
                title="Google Connected!",
                message=CONNECT_SUCCESS_MESSAGE,
                token_section=""
            ))
        else:
            # Login/signup flow
            user_info = await google_integration.get_user_info(tokens["raw_token"])
            email = user_info.get("email")
            
            if not email:
                raise Exception("Could not get email from Google")
            
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    email=email,
                    hashed_password=None,
                    auth_provider="google",
                    google_access_token=tokens["access_token"],
                    google_refresh_token=tokens.get("refresh_token")
                )
                db.add(user)
            else:
                user.google_access_token = tokens["access_token"]
                if tokens.get("refresh_token"):
                    user.google_refresh_token = tokens["refresh_token"]
            
            await db.commit()
            await db.refresh(user)
            
            jwt_token = create_access_token({"sub": str(user.id)})
            
            # For mobile, redirect back to app with token
            if platform == "mobile":
                return RedirectResponse(url=f"donna://auth/callback?token={jwt_token}&email={email}")
            
            return HTMLResponse(content=OAUTH_SUCCESS_HTML.format(
                title="Login Successful!",
                message="You can now close this window and return to the app.",
                token_section=TOKEN_SECTION.format(token=jwt_token)
            ))
        
    except Exception as e:
        error_msg = str(e)
        # For mobile, redirect with error
        if state:
            state_data = decode_state(state)
            if state_data.get("platform") == "mobile":
                return RedirectResponse(url=f"donna://auth/callback?error={error_msg}")
        
        return HTMLResponse(
            content=f"""
            <html><body style="font-family: sans-serif; text-align: center; padding: 2rem; background: #0f172a; color: #e2e8f0;">
                <h1 style="color: #f87171;">Authentication Failed</h1>
                <p style="color: #94a3b8;">{error_msg}</p>
                <p style="color: #64748b;">Please close this window and try again.</p>
            </body></html>
            """,
            status_code=400
        )

# ============================================
# Microsoft OAuth
# ============================================

@router.get("/microsoft")
async def microsoft_auth(platform: str = Query(default="desktop")):
    """Start Microsoft OAuth flow for login/signup."""
    state = encode_state({"action": "login", "platform": platform})
    return {"auth_url": microsoft_integration.get_auth_url(state=state)}

@router.get("/microsoft/connect")
async def microsoft_connect(user: User = Depends(get_current_user)):
    """For already logged-in users who want to connect Microsoft."""
    state = encode_state({"action": "connect", "user_id": str(user.id)})
    return {"auth_url": microsoft_integration.get_auth_url(state=state)}

@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Microsoft OAuth callback - handles both login and connect flows."""
    try:
        state_data = decode_state(state) if state else {}
        action = state_data.get("action", "login")
        platform = state_data.get("platform", "desktop")
        
        # Exchange code for tokens
        tokens = await microsoft_integration.exchange_code(code)
        
        if action == "connect" and state_data.get("user_id"):
            # Connect flow - update existing user
            user_id = state_data["user_id"]
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise Exception("User not found")
            
            user.microsoft_access_token = tokens["access_token"]
            if tokens.get("refresh_token"):
                user.microsoft_refresh_token = tokens["refresh_token"]
            
            await db.commit()
            
            # For mobile, redirect back to app
            if platform == "mobile":
                return RedirectResponse(url="donna://auth/callback?status=connected&provider=microsoft")
            
            return HTMLResponse(content=OAUTH_SUCCESS_HTML.format(
                title="Microsoft Connected!",
                message=CONNECT_SUCCESS_MESSAGE,
                token_section=""
            ))
        else:
            # Login/signup flow
            user_info = await microsoft_integration.get_user_info(tokens["raw_token"])
            email = user_info.get("email")
            
            if not email:
                raise Exception("Could not get email from Microsoft")
            
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    email=email,
                    hashed_password=None,
                    auth_provider="microsoft",
                    microsoft_access_token=tokens["access_token"],
                    microsoft_refresh_token=tokens.get("refresh_token")
                )
                db.add(user)
            else:
                user.microsoft_access_token = tokens["access_token"]
                if tokens.get("refresh_token"):
                    user.microsoft_refresh_token = tokens["refresh_token"]
            
            await db.commit()
            await db.refresh(user)
            
            jwt_token = create_access_token({"sub": str(user.id)})
            
            # For mobile, redirect back to app with token
            if platform == "mobile":
                return RedirectResponse(url=f"donna://auth/callback?token={jwt_token}&email={email}")
            
            return HTMLResponse(content=OAUTH_SUCCESS_HTML.format(
                title="Login Successful!",
                message="You can now close this window and return to the app.",
                token_section=TOKEN_SECTION.format(token=jwt_token)
            ))
        
    except Exception as e:
        error_msg = str(e)
        # For mobile, redirect with error
        if state:
            state_data = decode_state(state)
            if state_data.get("platform") == "mobile":
                return RedirectResponse(url=f"donna://auth/callback?error={error_msg}")
        
        return HTMLResponse(
            content=f"""
            <html><body style="font-family: sans-serif; text-align: center; padding: 2rem; background: #0f172a; color: #e2e8f0;">
                <h1 style="color: #f87171;">Authentication Failed</h1>
                <p style="color: #94a3b8;">{error_msg}</p>
                <p style="color: #64748b;">Please close this window and try again.</p>
            </body></html>
            """,
            status_code=400
        )

# ============================================
# Slack OAuth
# ============================================

@router.get("/slack")
async def slack_auth(platform: str = Query(default="desktop")):
    """Start Slack OAuth flow for login/signup."""
    state = encode_state({"action": "login", "platform": platform})
    return {"auth_url": get_slack_auth_url(state=state)}

@router.get("/slack/connect")
async def slack_connect(user: User = Depends(get_current_user)):
    """For already logged-in users who want to connect Slack."""
    state = encode_state({"action": "connect", "user_id": str(user.id)})
    return {"auth_url": get_slack_auth_url(state=state)}

@router.get("/slack/callback")
async def slack_callback(
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Slack OAuth callback - handles both login and connect flows."""
    try:
        state_data = decode_state(state) if state else {}
        action = state_data.get("action", "login")
        platform = state_data.get("platform", "desktop")
        
        # Exchange code for tokens
        tokens = await exchange_slack_code(code)
        
        if action == "connect" and state_data.get("user_id"):
            # Connect flow - create or update MessagingAccount
            user_id = state_data["user_id"]
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise Exception("User not found")
            
            team_id = tokens.get("team_id", "")
            team_name = tokens.get("team_name", "")
            
            # Check if MessagingAccount already exists for this user and team
            existing = await db.execute(
                select(MessagingAccount)
                .where(MessagingAccount.user_id == user.id)
                .where(MessagingAccount.platform == "slack")
                .where(MessagingAccount.account_id == team_id)
            )
            account = existing.scalar_one_or_none()
            
            if account:
                # Update existing account
                account.bot_token = tokens["access_token"]
                account.account_name = team_name
                account.is_active = True
            else:
                # Create new account
                account = MessagingAccount(
                    user_id=user.id,
                    platform="slack",
                    account_id=team_id,
                    account_name=team_name,
                    bot_token=tokens["access_token"],
                    is_active=True
                )
                db.add(account)
            
            await db.commit()
            
            # For mobile, redirect back to app
            if platform == "mobile":
                return RedirectResponse(url="donna://auth/callback?status=connected&provider=slack")
            
            return HTMLResponse(content=OAUTH_SUCCESS_HTML.format(
                title="Slack Connected!",
                message=CONNECT_SUCCESS_MESSAGE,
                token_section=""
            ))
        else:
            # Login/signup flow - create user if needed, then create MessagingAccount
            user_info = await get_slack_user_info(tokens["raw_token"])
            team_id = user_info.get("team_id", tokens.get("team_id", ""))
            team_name = user_info.get("team_name", tokens.get("team_name", ""))
            
            # For Slack, we use team_id as the identifier
            # We need to create a user - use team email or generate one
            # Since Slack doesn't provide email in OAuth, we'll use team_id@slack.local
            email = f"{team_id}@slack.local"
            
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    email=email,
                    hashed_password=None,
                    auth_provider="slack"
                )
                db.add(user)
                await db.flush()  # Get user ID
            
            # Create or update MessagingAccount
            existing = await db.execute(
                select(MessagingAccount)
                .where(MessagingAccount.user_id == user.id)
                .where(MessagingAccount.platform == "slack")
                .where(MessagingAccount.account_id == team_id)
            )
            account = existing.scalar_one_or_none()
            
            if account:
                account.bot_token = tokens["access_token"]
                account.account_name = team_name
                account.is_active = True
            else:
                account = MessagingAccount(
                    user_id=user.id,
                    platform="slack",
                    account_id=team_id,
                    account_name=team_name,
                    bot_token=tokens["access_token"],
                    is_active=True
                )
                db.add(account)
            
            await db.commit()
            await db.refresh(user)
            
            jwt_token = create_access_token({"sub": str(user.id)})
            
            # For mobile, redirect back to app with token
            if platform == "mobile":
                return RedirectResponse(url=f"donna://auth/callback?token={jwt_token}&email={email}")
            
            return HTMLResponse(content=OAUTH_SUCCESS_HTML.format(
                title="Login Successful!",
                message="You can now close this window and return to the app.",
                token_section=TOKEN_SECTION.format(token=jwt_token)
            ))
        
    except Exception as e:
        error_msg = str(e)
        # For mobile, redirect with error
        if state:
            state_data = decode_state(state)
            if state_data.get("platform") == "mobile":
                return RedirectResponse(url=f"donna://auth/callback?error={error_msg}")
        
        return HTMLResponse(
            content=f"""
            <html><body style="font-family: sans-serif; text-align: center; padding: 2rem; background: #0f172a; color: #e2e8f0;">
                <h1 style="color: #f87171;">Authentication Failed</h1>
                <p style="color: #94a3b8;">{error_msg}</p>
                <p style="color: #64748b;">Please close this window and try again.</p>
            </body></html>
            """,
            status_code=400
        )
