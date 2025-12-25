"""
Security utilities for the CV Builder application.
"""
import json
import re
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, Header
from ..utils.debug import print_step

# SQS message size limit is 256KB
# We use a slightly lower limit to account for metadata overhead
SQS_MESSAGE_SIZE_LIMIT_BYTES = 240_000

def sanitize_user_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    
    Args:
        text: User input text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove potentially dangerous characters
    # This is a basic sanitization - consider using a proper HTML sanitizer
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    return text.strip()

def validate_job_description(job_description: str) -> str:
    """
    Validate and sanitize job description input.
    
    Args:
        job_description: Job description text
        
    Returns:
        Validated and sanitized job description
        
    Raises:
        HTTPException: If validation fails
    """
    if not job_description or not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description is required"
        )
    
    # Sanitize input
    sanitized = sanitize_user_input(job_description, max_length=50000)
    
    if len(sanitized) < 10:
        raise HTTPException(
            status_code=400,
            detail="Job description must be at least 10 characters long"
        )
    
    return sanitized

def validate_cv_text(cv_text: str) -> str:
    """
    Validate and sanitize CV text input.
    
    Args:
        cv_text: CV text content
        
    Returns:
        Validated and sanitized CV text
        
    Raises:
        HTTPException: If validation fails
    """
    if not cv_text or not cv_text.strip():
        raise HTTPException(
            status_code=400,
            detail="CV text is required"
        )
    
    # Sanitize input
    sanitized = sanitize_user_input(cv_text, max_length=100000)
    
    if len(sanitized) < 50:
        raise HTTPException(
            status_code=400,
            detail="CV text must be at least 50 characters long"
        )
    
    return sanitized


def get_user_llm_config(
    x_user_provider: Optional[str] = Header(None, alias="X-User-Provider"),
    x_user_api_key: Optional[str] = Header(None, alias="X-User-Api-Key"),
) -> Optional[Tuple[str, str]]:
    """
    FastAPI dependency to extract and validate BYOK (Bring Your Own Key) headers.
    
    Args:
        x_user_provider: User's AI provider (openai or gemini)
        x_user_api_key: User's API key for the provider
        
    Returns:
        Tuple of (provider, api_key) if both present, None if both absent
        
    Raises:
        HTTPException: If validation fails
    """
    # Both absent → free tier fallback
    if not x_user_provider and not x_user_api_key:
        return None
    
    # Only one present → invalid
    if not x_user_provider:
        raise HTTPException(
            status_code=400,
            detail="X-User-Provider header is required when X-User-Api-Key is provided"
        )
    if not x_user_api_key:
        raise HTTPException(
            status_code=400,
            detail="X-User-Api-Key header is required when X-User-Provider is provided"
        )
    
    # Trim and validate
    provider = x_user_provider.strip().lower()
    api_key = x_user_api_key.strip()
    
    # Validate provider
    if provider not in ("openai", "gemini"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}. Supported providers: openai, gemini"
        )
    
    # Validate key length
    if len(api_key) > 512:
        raise HTTPException(
            status_code=400,
            detail="API key exceeds maximum allowed length (512 characters)"
        )
    
    if len(api_key) < 10:
        raise HTTPException(
            status_code=400,
            detail="API key is too short (minimum 10 characters)"
        )
    
    # Log presence only (never log the actual key or prefix)
    print_step("BYOK Config", {
        "provider": provider,
        "api_key_length": len(api_key),
    }, "input")
    
    return (provider, api_key)


def validate_sqs_message_size(payload: Dict[str, Any]) -> None:
    """
    Validate that a payload will fit within SQS message size limits.
    
    This prevents enqueue failures for large payloads (e.g., cv_json in evaluate jobs).
    SQS limit is 256KB, but we use a conservative 240KB to account for metadata.
    
    Plan: local-first_vault_c7381a99
    
    Args:
        payload: The payload dict that will be sent to SQS
        
    Raises:
        HTTPException: If payload exceeds size limit
    """
    try:
        # Serialize to JSON to get actual byte size
        payload_json = json.dumps(payload, ensure_ascii=False)
        payload_bytes = payload_json.encode('utf-8')
        size_bytes = len(payload_bytes)
        
        if size_bytes > SQS_MESSAGE_SIZE_LIMIT_BYTES:
            size_kb = size_bytes / 1024
            limit_kb = SQS_MESSAGE_SIZE_LIMIT_BYTES / 1024
            raise HTTPException(
                status_code=413,  # Payload Too Large
                detail=(
                    f"Request payload is too large ({size_kb:.1f}KB). "
                    f"Maximum allowed is {limit_kb:.1f}KB. "
                    "Please reduce the size of your CV or job description."
                )
            )
    except (TypeError, ValueError) as e:
        # Should not happen, but catch serialization errors
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payload format: {str(e)}"
        )
