"""
License validation service for verifying Managed tier subscriptions.

This service queries DynamoDB to verify that a license key corresponds to an active
subscription, enabling server-side tier verification (security boundary).
"""

from __future__ import annotations

from typing import Optional
from ..core.config import settings
from .dynamo_license_subscription_repository import DynamoLicenseSubscriptionRepository


class LicenseValidationService:
    """Service for validating license keys and subscription status."""
    
    def __init__(self, repository: Optional[DynamoLicenseSubscriptionRepository] = None):
        """
        Initialize the license validation service.
        
        Args:
            repository: Optional repository instance (for testing). If None, creates
                      a new DynamoLicenseSubscriptionRepository using settings.
        """
        if repository is None:
            if not settings.LICENSE_SUBSCRIPTIONS_TABLE_NAME:
                raise ValueError("LICENSE_SUBSCRIPTIONS_TABLE_NAME is not configured")
            self._repo = DynamoLicenseSubscriptionRepository(settings.LICENSE_SUBSCRIPTIONS_TABLE_NAME)
        else:
            self._repo = repository
    
    def verify_managed_tier(self, license_key: str) -> bool:
        """
        Verify that a license key corresponds to an active Managed tier subscription.
        
        Args:
            license_key: The license key ID from LemonSqueezy (frontend sends this as X-License-Key)
                        This should be the license_key_id (numeric ID), not the full license key string.
                        The frontend can obtain this from the LemonSqueezy license activation response.
            
        Returns:
            True if subscription is active, False otherwise
            
        Note:
            TODO: If frontend sends full license key string instead of license_key_id, we need to:
            1. Call LemonSqueezy API to resolve license_key -> license_key_id, OR
            2. Store a mapping (license_key -> license_key_id) in DynamoDB
        """
        if not license_key:
            return False
        
        # Query DynamoDB by license_key_id (assuming frontend sends license_key_id)
        # If frontend sends full license key, we may need to resolve it first
        subscription = self._repo.get_subscription_by_license_key_id(license_key)
        
        if not subscription:
            return False
        
        status = subscription.get("status")
        if status != "active":
            return False
        
        # Check if subscription has ended (for cancelled subscriptions)
        ends_at = subscription.get("ends_at")
        if ends_at:
            import time
            current_time = int(time.time())
            if current_time >= ends_at:
                return False
        
        return True

