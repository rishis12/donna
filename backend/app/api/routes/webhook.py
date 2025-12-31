"""Webhook endpoints for external services."""
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from typing import Optional
import hmac
import hashlib
import time
import json
import logging
from ...core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["webhook"])

@router.post("/calendar")
async def calendar_webhook(
    request: Request,
    x_slack_signature: Optional[str] = Header(None),
    x_slack_request_timestamp: Optional[str] = Header(None)
):
    """
    Webhook endpoint for calendar events (Google Calendar, Outlook, etc.)
    Can be extended to handle specific calendar providers.
    """
    try:
        body = await request.body()
        body_text = await request.body()
        
        # Basic webhook validation (extend based on provider)
        # For Google Calendar, you'd validate using Google's method
        # For Slack, validate signature
        
        logger.info(f"Calendar webhook received: {len(body)} bytes")
        
        return {
            "status": "received",
            "message": "Webhook processed successfully"
        }
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slack")
async def slack_webhook(
    request: Request,
    x_slack_signature: Optional[str] = Header(None),
    x_slack_request_timestamp: Optional[str] = Header(None)
):
    """
    Slack webhook endpoint with signature verification.
    """
    if not settings.slack_signing_secret:
        raise HTTPException(status_code=500, detail="Slack signing secret not configured")
    
    try:
        body = await request.body()
        body_text = body.decode('utf-8')
        
        # Verify Slack signature
        if x_slack_signature and x_slack_request_timestamp:
            timestamp = int(x_slack_request_timestamp)
            
            # Check timestamp (prevent replay attacks)
            if abs(time.time() - timestamp) > 60 * 5:  # 5 minutes
                raise HTTPException(status_code=400, detail="Request timestamp too old")
            
            # Create signature base string
            sig_basestring = f"v0:{timestamp}:{body_text}"
            
            # Calculate signature
            my_signature = 'v0=' + hmac.new(
                settings.slack_signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            if not hmac.compare_digest(my_signature, x_slack_signature):
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Process webhook (parse JSON, handle events, etc.)
        data = json.loads(body_text)
        
        logger.info(f"Slack webhook received: {data.get('type', 'unknown')}")
        
        # Handle Slack challenge (for URL verification)
        if data.get('type') == 'url_verification':
            return {"challenge": data.get('challenge')}
        
        return {"status": "ok"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Slack webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "endpoints": {
            "calendar": "/webhook/calendar",
            "slack": "/webhook/slack"
        }
    }

