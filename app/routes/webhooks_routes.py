"""
LemonSqueezy Webhooks

Handles webhook events from LemonSqueezy for subscription lifecycle management.
Verifies HMAC signatures and processes events like subscription cancellation,
expiration, and refunds.
"""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
import json
import logging
import time
from ..core.config import settings
from ..services.dynamo_license_subscription_repository import DynamoLicenseSubscriptionRepository

logger = logging.getLogger(__name__)

# Initialize repository (lazy initialization)
_repo: Optional[DynamoLicenseSubscriptionRepository] = None

def _get_repo() -> DynamoLicenseSubscriptionRepository:
    """Get or create the license subscription repository."""
    global _repo
    if _repo is None:
        if not settings.LICENSE_SUBSCRIPTIONS_TABLE_NAME:
            logger.error("LICENSE_SUBSCRIPTIONS_TABLE_NAME is not configured")
            raise HTTPException(status_code=500, detail="License subscriptions table not configured")
        _repo = DynamoLicenseSubscriptionRepository(settings.LICENSE_SUBSCRIPTIONS_TABLE_NAME)
    return _repo

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature")
):
    """
    Handle LemonSqueezy webhook events.
    
    Verifies HMAC signature and processes subscription lifecycle events:
    - subscription_created
    - subscription_updated
    - subscription_cancelled
    - subscription_resumed
    - subscription_expired
    - order_refunded
    
    Security:
    - HMAC SHA-256 signature verification prevents spoofed requests
    - Only processes events from verified LemonSqueezy origin
    """
    from app.core.config import settings
    
    # Read raw body (needed for signature verification)
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # Verify signature
    if not x_signature:
        logger.error("Webhook received without X-Signature header")
        raise HTTPException(status_code=401, detail="Missing X-Signature header")
    
    if not settings.LEMONSQUEEZY_WEBHOOK_SECRET:
        logger.error("LEMONSQUEEZY_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    # Calculate expected signature
    expected_signature = hmac.new(
        settings.LEMONSQUEEZY_WEBHOOK_SECRET.encode('utf-8'),
        body_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison to prevent timing attacks)
    if not hmac.compare_digest(x_signature, expected_signature):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.info("Webhook signature verified")
    
    # Parse event
    try:
        event_data = json.loads(body_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    event_name = event_data.get('meta', {}).get('event_name')
    
    logger.info(f"Received webhook event: {event_name}")
    
    # Handle subscription events
    try:
        if event_name == 'subscription_cancelled':
            await handle_subscription_cancelled(event_data)
        elif event_name == 'subscription_expired':
            await handle_subscription_expired(event_data)
        elif event_name == 'subscription_resumed':
            await handle_subscription_resumed(event_data)
        elif event_name == 'order_refunded':
            await handle_order_refunded(event_data)
        elif event_name == 'subscription_created':
            await handle_subscription_created(event_data)
        elif event_name == 'subscription_updated':
            await handle_subscription_updated(event_data)
        else:
            logger.info(f"Unhandled event type: {event_name}")
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}")
        # Don't raise HTTP error - return 200 to LemonSqueezy so they don't retry
        # Log the error for manual investigation
    
    return {"status": "ok"}


async def handle_subscription_created(event_data: dict):
    """
    Handle subscription_created event.
    Triggered when a new managed subscription is created.
    """
    subscription_id = event_data['data']['id']
    license_key_id = event_data['data']['relationships'].get('license-keys', {}).get('data', [{}])[0].get('id')
    customer_email = event_data['data']['attributes']['user_email']
    created_at = event_data['data']['attributes'].get('created_at')
    
    logger.info(f"Subscription created: {subscription_id} for {customer_email}")
    logger.info(f"   License key ID: {license_key_id}")
    
    # Store subscription info in DynamoDB for backend license validation
    repo = _get_repo()
    created_at_ts = int(time.time())
    if created_at:
        try:
            # Parse ISO 8601 timestamp if provided
            from datetime import datetime
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            created_at_ts = int(dt.timestamp())
        except Exception:
            pass  # Use current time if parsing fails
    
    repo.create_subscription(
        subscription_id=subscription_id,
        license_key_id=license_key_id,
        status="active",
        customer_email=customer_email,
        created_at=created_at_ts,
    )


async def handle_subscription_updated(event_data: dict):
    """
    Handle subscription_updated event.
    Triggered when subscription details change (e.g., plan upgrade).
    """
    subscription_id = event_data['data']['id']
    status = event_data['data']['attributes']['status']
    renews_at = event_data['data']['attributes'].get('renews_at')
    
    logger.info(f"Subscription updated: {subscription_id}, new status: {status}")
    
    # Update subscription status in DynamoDB
    repo = _get_repo()
    renews_at_ts = None
    if renews_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
            renews_at_ts = int(dt.timestamp())
        except Exception:
            pass
    
    # Map LemonSqueezy status to our status
    our_status = "active" if status in ("active", "trialing") else status
    
    repo.update_subscription_status(
        subscription_id=subscription_id,
        status=our_status,
        renews_at=renews_at_ts,
    )


async def handle_subscription_cancelled(event_data: dict):
    """
    Mark license as revoked when subscription is cancelled.
    The license will become invalid after the current billing period ends.
    """
    subscription_id = event_data['data']['id']
    ends_at = event_data['data']['attributes'].get('ends_at')
    
    logger.warning(f"Subscription cancelled: {subscription_id}")
    logger.info(f"   Access ends at: {ends_at}")
    
    # Update subscription status in DynamoDB
    repo = _get_repo()
    ends_at_ts = None
    if ends_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(ends_at.replace('Z', '+00:00'))
            ends_at_ts = int(dt.timestamp())
        except Exception:
            pass
    
    repo.update_subscription_status(
        subscription_id=subscription_id,
        status="cancelled",
        ends_at=ends_at_ts,
    )
    
    # Frontend will get 'valid: false' when it tries to revalidate after ends_at


async def handle_subscription_expired(event_data: dict):
    """
    Handle subscription expiry (end of billing period after cancellation).
    License becomes invalid immediately.
    """
    subscription_id = event_data['data']['id']
    
    logger.warning(f"Subscription expired: {subscription_id}")
    
    # Mark license as expired in DynamoDB
    repo = _get_repo()
    repo.update_subscription_status(
        subscription_id=subscription_id,
        status="expired",
    )
    
    # Frontend will get 'valid: false' on next revalidation


async def handle_subscription_resumed(event_data: dict):
    """
    Re-enable license when subscription is resumed after cancellation.
    """
    subscription_id = event_data['data']['id']
    renews_at = event_data['data']['attributes'].get('renews_at')
    
    logger.info(f"Subscription resumed: {subscription_id}")
    logger.info(f"   Next renewal: {renews_at}")
    
    # Update subscription status in DynamoDB
    repo = _get_repo()
    renews_at_ts = None
    if renews_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
            renews_at_ts = int(dt.timestamp())
        except Exception:
            pass
    
    repo.update_subscription_status(
        subscription_id=subscription_id,
        status="active",
        renews_at=renews_at_ts,
    )
    
    # Frontend will get 'valid: true' on next revalidation


async def handle_order_refunded(event_data: dict):
    """
    Revoke license when order is refunded.
    Applies to both lifetime (BYOK) and subscription purchases.
    
    Note: This event may include subscription_id in relationships.
    We need to find all subscriptions associated with this order and mark them as refunded.
    """
    order_id = event_data['data']['id']
    refunded_at = event_data['data']['attributes'].get('refunded_at')
    
    logger.warning(f"Order refunded: {order_id} at {refunded_at}")
    
    # Extract subscription IDs from order relationships
    subscriptions = event_data['data'].get('relationships', {}).get('subscriptions', {}).get('data', [])
    
    repo = _get_repo()
    for sub_data in subscriptions:
        subscription_id = sub_data.get('id')
        if subscription_id:
            # Mark subscription as refunded
            repo.update_subscription_status(
                subscription_id=subscription_id,
                status="refunded",
            )
            logger.info(f"   Marked subscription {subscription_id} as refunded")
    
    # Frontend will get 'valid: false' on next revalidation

