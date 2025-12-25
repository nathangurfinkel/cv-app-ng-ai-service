"""
DynamoDB implementation of LicenseSubscriptionRepository.
"""

from __future__ import annotations

import time
from typing import Optional

import boto3

from .license_subscription_repository import LicenseSubscriptionRepository


class DynamoLicenseSubscriptionRepository(LicenseSubscriptionRepository):
    """DynamoDB implementation for license subscriptions."""
    
    def __init__(self, table_name: str):
        self._table = boto3.resource("dynamodb").Table(table_name)
    
    def get_subscription_by_license_key_id(self, license_key_id: str) -> Optional[dict]:
        """
        Get subscription by license_key_id using GSI.
        
        Args:
            license_key_id: The license key ID from LemonSqueezy
            
        Returns:
            Subscription dict if found, None otherwise
        """
        try:
            response = self._table.query(
                IndexName="license_key_id-index",
                KeyConditionExpression="license_key_id = :lkid",
                ExpressionAttributeValues={":lkid": license_key_id},
            )
            items = response.get("Items", [])
            if items:
                return items[0]
            return None
        except Exception:
            # If GSI doesn't exist or query fails, return None
            return None
    
    def get_subscription_by_id(self, subscription_id: str) -> Optional[dict]:
        """
        Get subscription by subscription_id (primary key).
        
        Args:
            subscription_id: The subscription ID from LemonSqueezy
            
        Returns:
            Subscription dict if found, None otherwise
        """
        try:
            response = self._table.get_item(Key={"subscription_id": subscription_id})
            return response.get("Item")
        except Exception:
            return None
    
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
        """
        Create a new subscription record.
        
        Args:
            subscription_id: Primary key (subscription ID from LemonSqueezy)
            license_key_id: License key ID (for GSI lookup)
            status: Subscription status ("active", "cancelled", "expired")
            customer_email: Customer email address
            created_at: Unix timestamp when subscription was created
            ends_at: Optional Unix timestamp when subscription ends (for cancelled subscriptions)
            renews_at: Optional Unix timestamp when subscription renews
        """
        item = {
            "subscription_id": subscription_id,
            "license_key_id": license_key_id,
            "status": status,
            "customer_email": customer_email,
            "created_at": created_at,
        }
        
        if ends_at is not None:
            item["ends_at"] = ends_at
        if renews_at is not None:
            item["renews_at"] = renews_at
        
        self._table.put_item(Item=item)
    
    def update_subscription_status(
        self,
        *,
        subscription_id: str,
        status: str,
        ends_at: Optional[int] = None,
        renews_at: Optional[int] = None,
    ) -> None:
        """
        Update subscription status.
        
        Args:
            subscription_id: Primary key
            status: New status ("active", "cancelled", "expired")
            ends_at: Optional Unix timestamp when subscription ends
            renews_at: Optional Unix timestamp when subscription renews
        """
        now = int(time.time())
        update_expr = ["#s = :s"]
        expr_names = {"#s": "status"}
        expr_values = {":s": status}
        
        if ends_at is not None:
            update_expr.append("ends_at = :ea")
            expr_values[":ea"] = ends_at
        elif status == "active":
            # Clear ends_at if reactivating
            update_expr.append("ends_at = :ea")
            expr_values[":ea"] = None
        
        if renews_at is not None:
            update_expr.append("renews_at = :ra")
            expr_values[":ra"] = renews_at
        
        self._table.update_item(
            Key={"subscription_id": subscription_id},
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

