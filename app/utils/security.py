"""
Security utilities for the CV Builder application.
"""
import re
from fastapi import HTTPException
from ..utils.debug import print_step

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
