from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import hmac
import hashlib
import time
import json
from ..schemas import MessagingAccountCreate, MessagingAccountResponse, MessagingMessageSend
from ..deps import get_current_user
from ...core.database import get_db
from ...core.config import get_settings
from ...core.security import decrypt_token
from ...models.user import User
from ...models.messaging_account import MessagingAccount
from ...integrations.discord_integration import discord_integration
from ...integrations.slack_integration import slack_integration

router = APIRouter(prefix="/messaging-accounts", tags=["messaging-accounts"])

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify the router is accessible."""
    return {"status": "ok", "message": "Messaging accounts router is working"}

@router.get("/", response_model=List[MessagingAccountResponse])
async def list_messaging_accounts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List all messaging accounts for the current user."""
    result = await db.execute(
        select(MessagingAccount).where(MessagingAccount.user_id == user.id)
    )
    accounts = result.scalars().all()
    return accounts

@router.post("/", response_model=MessagingAccountResponse)
async def add_messaging_account(
    account_data: MessagingAccountCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Add a new messaging account (Discord or Slack)."""
    try:
        # Validate platform
        if account_data.platform not in ['discord', 'slack']:
            raise HTTPException(status_code=400, detail="Invalid platform. Must be 'discord' or 'slack'")

        # Create messaging account
        messaging_account = MessagingAccount(
            user_id=user.id,
            platform=account_data.platform,
            account_id=account_data.account_id,
            account_name=account_data.account_name,
            channel_id=account_data.channel_id,
            bot_token=account_data.bot_token,
            webhook_url=account_data.webhook_url,
            access_token=account_data.access_token
        )

        db.add(messaging_account)
        await db.commit()
        await db.refresh(messaging_account)

        return messaging_account

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add messaging account: {str(e)}")

@router.delete("/{account_id}")
async def delete_messaging_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Delete a messaging account."""
    result = await db.execute(
        select(MessagingAccount)
        .where(MessagingAccount.id == account_id)
        .where(MessagingAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Messaging account not found")

    await db.delete(account)
    await db.commit()

    return {"message": "Messaging account deleted"}

@router.post("/send-message")
async def send_message(
    message_data: MessagingMessageSend,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Send a message via a connected messaging account."""
    result = await db.execute(
        select(MessagingAccount)
        .where(MessagingAccount.user_id == user.id)
        .where(MessagingAccount.platform == message_data.platform)
        .where(MessagingAccount.account_id == message_data.account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Messaging account not found")

    try:
        if message_data.platform == "discord":
            if not account.bot_token:
                raise HTTPException(status_code=400, detail="Bot token required for Discord")
            response = await discord_integration.send_message(
                account.bot_token,
                message_data.channel_id or account.channel_id,
                message_data.message
            )

        elif message_data.platform == "slack":
            if not account.bot_token:
                raise HTTPException(status_code=400, detail="Bot token required for Slack")
            response = await slack_integration.send_message(
                account.bot_token,
                message_data.channel_id or account.channel_id,
                message_data.message
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")

        return {"status": "sent", "response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.post("/setup-webhook")
async def setup_webhook(
    platform: str,
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Setup webhook for a messaging account."""
    result = await db.execute(
        select(MessagingAccount)
        .where(MessagingAccount.user_id == user.id)
        .where(MessagingAccount.platform == platform)
        .where(MessagingAccount.account_id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Messaging account not found")

    from ...core.config import get_settings
    settings = get_settings()

    try:
        if platform == "discord":
            # Discord uses different webhook setup
            return {"status": "discord_webhook_setup_required", "message": "Discord webhooks are set up per channel"}

        elif platform == "slack":
            # Slack webhooks are set up in the Slack app dashboard
            return {"status": "slack_webhook_setup_required", "message": "Slack webhooks are configured in Slack app"}

        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup webhook: {str(e)}")

@router.post("/webhook/discord")
async def discord_webhook(request: dict):
    """Handle incoming Discord webhook messages."""
    # Process incoming message and forward to Donna
    return {"status": "received"}

def verify_slack_signature(timestamp: str, body: str, signature: str, signing_secret: str) -> bool:
    """Verify Slack request signature."""
    if not signing_secret:
        print("[WARNING] No signing secret configured, skipping signature verification")
        return True  # Allow if no secret configured (for development)
    
    # Check timestamp to prevent replay attacks (within 5 minutes)
    current_time = int(time.time())
    if abs(current_time - int(timestamp)) > 60 * 5:
        print(f"[WARNING] Request timestamp too old: {timestamp} vs {current_time}")
        return False
    
    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{body}"
    
    # Create the signature
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures using constant-time comparison
    return hmac.compare_digest(my_signature, signature)

@router.post("/webhook/slack")
async def slack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Slack Events API webhook messages."""
    print(f"[WEBHOOK] Received request to /webhook/slack")
    print(f"[WEBHOOK] Headers: {dict(request.headers)}")
    try:
        # Get raw body for signature verification
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        print(f"[WEBHOOK] Body length: {len(body_str)}")
        
        # Parse JSON body first to check for URL verification challenge
        # (URL verification doesn't require signature verification)
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            return {"status": "error", "message": "Invalid JSON"}
        
        # Handle URL verification challenge FIRST (before signature verification)
        # Slack sends this during initial setup and doesn't include a signature
        if body.get("type") == "url_verification":
            challenge = body.get("challenge")
            print(f"[INFO] Slack URL verification challenge: {challenge}")
            return {"challenge": challenge}
        
        # For all other requests, verify signature
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        
        settings = get_settings()
        signing_secret = settings.slack_signing_secret
        
        if not verify_slack_signature(timestamp, body_str, signature, signing_secret):
            print("[ERROR] Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        print(f"[INFO] Received Slack webhook: {body.get('type')}")
        
        # Handle event callbacks
        if body.get("type") == "event_callback":
            event = body.get("event", {})
            event_type = event.get("type")
            
            # Only process message events
            if event_type == "message":
                # Ignore bot messages and message subtypes (edits, deletions, etc.)
                if event.get("bot_id") or event.get("subtype"):
                    print(f"[INFO] Ignoring bot message or subtype: {event.get('subtype')}")
                    return {"status": "ok"}
                
                # Get message details
                channel = event.get("channel")
                text = event.get("text", "")
                user_id = event.get("user")
                thread_ts = event.get("thread_ts")
                ts = event.get("ts")
                
                if not text:
                    print("[INFO] No text in message")
                    return {"status": "ok"}
                
                print(f"[INFO] Processing message from channel {channel}: '{text[:50]}...'")
                
                # Find a messaging account for this Slack workspace
                try:
                    result = await db.execute(
                        select(MessagingAccount)
                        .where(MessagingAccount.platform == "slack")
                        .where(MessagingAccount.is_active == True)
                    )
                    accounts = result.scalars().all()
                except Exception as db_err:
                    print(f"[ERROR] Database query failed: {db_err}")
                    accounts = []
                
                account = None
                user = None
                bot_token = settings.slack_bot_token
                
                # Find the first active account with a user
                for acc in accounts:
                    if acc.user:
                        account = acc
                        user = acc.user
                        # Decrypt bot token if stored
                        if acc.bot_token:
                            try:
                                bot_token = decrypt_token(acc.bot_token)
                            except:
                                # If decryption fails, use settings token
                                pass
                        break
                
                # If no account found, try to find any user (fallback for testing)
                if not user:
                    try:
                        result = await db.execute(select(User).limit(1))
                        user = result.scalar_one_or_none()
                    except Exception as db_err:
                        print(f"[ERROR] Failed to get user: {db_err}")
                        user = None
                
                if not user:
                    print("[ERROR] No user found for Slack webhook")
                    return {"status": "error", "message": "No user configured"}
                
                if not bot_token:
                    print("[ERROR] No bot token available")
                    return {"status": "error", "message": "Bot token not configured"}
                
                # Process the message with Donna
                from ...services.llm_service import parse_utterance
                from ...api.routes.utterance import get_conversation_history, get_user_calendar_context
                from datetime import datetime, timezone
                
                try:
                    # Get conversation history
                    history = await get_conversation_history(db, str(user.id))
                    
                    # Get calendar context if needed
                    calendar_context = await get_user_calendar_context(user)
                    
                    # Parse the utterance
                    llm_result = await parse_utterance(
                        text,
                        datetime.now(timezone.utc).isoformat(),
                        history,
                        "UTC",  # Default timezone
                        calendar_context
                    )
                    
                    # Send Donna's response back to Slack
                    response_text = llm_result.get("response", "I'm not sure how to respond to that.")
                    print(f"[INFO] Donna responding: '{response_text[:50]}...'")
                    
                    # Send response in thread if original message was in a thread
                    response_ts = thread_ts if thread_ts else ts
                    
                    try:
                        await slack_integration.send_message(
                            bot_token,
                            channel,
                            response_text,
                            thread_ts=response_ts if thread_ts else None
                        )
                        print(f"[INFO] Successfully sent response to Slack")
                    except Exception as send_err:
                        print(f"[ERROR] Failed to send Slack message: {send_err}")
                        import traceback
                        print(traceback.format_exc())
                        return {"status": "error", "message": f"Failed to send response: {str(send_err)}"}
                    
                    return {"status": "ok", "message": "Processed"}
                    
                except Exception as process_err:
                    print(f"[ERROR] Failed to process message: {process_err}")
                    import traceback
                    print(traceback.format_exc())
                    return {"status": "error", "message": f"Processing error: {str(process_err)}"}
            
            # Acknowledge other event types
            return {"status": "ok"}
        
        # Acknowledge other request types
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Slack webhook error: {error_trace}")
        # Return 200 OK to Slack so it doesn't retry
        return {"status": "error", "message": str(e)}
