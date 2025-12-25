"""
Tier validation utilities for gating premium features.

This module provides validation logic to ensure users have appropriate
tier access for AI operations and other premium features.
"""

from enum import Enum
from typing import Optional
from fastapi import HTTPException, Header
from ..services.license_validation_service import LicenseValidationService


class UserTier(str, Enum):
    """User tier levels matching frontend UserTier enum."""
    FREE = "free"
    BYOK = "byok_lifetime"
    MANAGED = "managed_subscription"


# Feature flags per tier
TIER_LIMITS = {
    UserTier.FREE: {
        "can_use_ai_operations": False,
        "can_use_mock_interviewer": False,
    },
    UserTier.BYOK: {
        "can_use_ai_operations": True,
        "can_use_mock_interviewer": False,
    },
    UserTier.MANAGED: {
        "can_use_ai_operations": True,
        "can_use_mock_interviewer": True,
    },
}


def validate_tier_for_operation(
    operation: str,
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier")
) -> UserTier:
    """
    Validates that the user's tier allows the requested operation.
    
    Args:
        operation: The operation type to validate ('ai_operations' or 'mock_interviewer')
        x_user_tier: The user tier from the X-User-Tier header
        
    Returns:
        UserTier: The validated user tier
        
    Raises:
        HTTPException: If the user's tier does not allow the operation
    """
    # Default to FREE tier if no header provided
    try:
        tier = UserTier(x_user_tier) if x_user_tier else UserTier.FREE
    except ValueError:
        # Invalid tier value, default to FREE
        tier = UserTier.FREE
    
    # Check AI operations access
    if operation == "ai_operations":
        if not TIER_LIMITS[tier]["can_use_ai_operations"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "tier_upgrade_required",
                    "message": "AI operations require BYOK Lifetime or Managed Subscription",
                    "current_tier": tier.value,
                    "required_tiers": ["byok_lifetime", "managed_subscription"]
                }
            )
    
    # Check mock interviewer access
    elif operation == "mock_interviewer":
        if not TIER_LIMITS[tier]["can_use_mock_interviewer"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "tier_upgrade_required",
                    "message": "Voice interviewer is exclusive to Managed Subscription",
                    "current_tier": tier.value,
                    "required_tiers": ["managed_subscription"]
                }
            )
    
    return tier


def verify_tier_with_license(
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier"),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
) -> UserTier:
    """
    Verify tier with license key for Managed tier (server-side verification).
    
    For MANAGED tier, requires X-License-Key header and verifies subscription status
    via DynamoDB. If verification fails, downgrades to FREE tier.
    
    Args:
        x_user_tier: The user tier from the X-User-Tier header
        x_license_key: The license key from the X-License-Key header (required for MANAGED tier)
        
    Returns:
        UserTier: The verified user tier (may be downgraded from MANAGED to FREE if verification fails)
    """
    # Default to FREE tier if no header provided
    try:
        tier = UserTier(x_user_tier) if x_user_tier else UserTier.FREE
    except ValueError:
        # Invalid tier value, default to FREE
        tier = UserTier.FREE
    
    # For MANAGED tier, verify license key
    if tier == UserTier.MANAGED:
        if not x_license_key:
            # No license key provided, downgrade to FREE
            return UserTier.FREE
        
        try:
            license_service = LicenseValidationService()
            is_valid = license_service.verify_managed_tier(x_license_key)
            if not is_valid:
                # License verification failed, downgrade to FREE
                return UserTier.FREE
        except Exception:
            # If license validation service fails (e.g., table not configured),
            # downgrade to FREE for security
            return UserTier.FREE
    
    return tier


def require_ai_operations(
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier"),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
) -> UserTier:
    """
    Dependency function to require AI operations tier access with license verification.
    
    Verifies MANAGED tier via license key (server-side). If verification fails,
    downgrades to FREE tier and raises 403.
    
    Usage in routes:
        @router.post("/jobs/extract")
        async def create_extract_job(
            request: ExtractRequest,
            tier: UserTier = Depends(require_ai_operations)
        ):
            ...
    """
    # Verify tier with license (may downgrade MANAGED to FREE)
    verified_tier = verify_tier_with_license(x_user_tier, x_license_key)
    
    # Check if verified tier allows AI operations
    if not TIER_LIMITS[verified_tier]["can_use_ai_operations"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tier_upgrade_required",
                "message": "AI operations require BYOK Lifetime or Managed Subscription",
                "current_tier": verified_tier.value,
                "required_tiers": ["byok_lifetime", "managed_subscription"]
            }
        )
    
    return verified_tier


def require_mock_interviewer(
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier"),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
) -> UserTier:
    """
    Dependency function to require mock interviewer tier access with license verification.
    
    Verifies MANAGED tier via license key (server-side). If verification fails,
    downgrades to FREE tier and raises 403.
    
    Usage in routes:
        @router.post("/interview/start")
        async def start_interview(
            request: InterviewRequest,
            tier: UserTier = Depends(require_mock_interviewer)
        ):
            ...
    """
    # Verify tier with license (may downgrade MANAGED to FREE)
    verified_tier = verify_tier_with_license(x_user_tier, x_license_key)
    
    # Check if verified tier allows mock interviewer
    if not TIER_LIMITS[verified_tier]["can_use_mock_interviewer"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tier_upgrade_required",
                "message": "Voice interviewer is exclusive to Managed Subscription",
                "current_tier": verified_tier.value,
                "required_tiers": ["managed_subscription"]
            }
        )
    
    return verified_tier


