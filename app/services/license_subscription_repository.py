"""
DynamoDB repository for LicenseSubscriptions table.

Stores subscription information from LemonSqueezy webhooks for backend tier verification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime


class LicenseSubscriptionRepository(ABC):
    """Abstract repository for license subscription data."""
    
    @abstractmethod
    def get_subscription_by_license_key_id(self, license_key_id: str) -> Optional[dict]:
        """Get subscription by license_key_id (via GSI)."""
        raise NotImplementedError
    
    @abstractmethod
    def create_subscription(
        self,
        *,
        subscription_id: str,
        license_key_id: str,
        status: str,
        customer_email: str,
        created_at: int,
        ends_at: Optional[int] = None,
        renews_at: Optional[int] = None,
    ) -> None:
        """Create a new subscription record."""
        raise NotImplementedError
    
    @abstractmethod
    def update_subscription_status(
        self,
        *,
        subscription_id: str,
        status: str,
        ends_at: Optional[int] = None,
        renews_at: Optional[int] = None,
    ) -> None:
        """Update subscription status."""
        raise NotImplementedError

