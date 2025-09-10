"""
Security utilities for the CV Builder application.
"""
import magic
import re
from pathlib import Path
from typing import Optional
from fastapi import HTTPException
from ..utils.debug import print_step

def validate_file_content(file_content: bytes, expected_type: str) -> bool:
    """
    Validate file content matches expected MIME type.
    
    Args:
        file_content: File content as bytes
        expected_type: Expected MIME type
        
    Returns:
        True if file content matches expected type
    """
    try:
        mime_type = magic.from_buffer(file_content, mime=True)
        print_step("File Content Validation", {
            "expected_type": expected_type,
            "detected_type": mime_type,
            "file_size": len(file_content)
        }, "input")
        
        is_valid = mime_type == expected_type
        print_step("File Content Validation", {
            "is_valid": is_valid,
            "mime_type": mime_type
        }, "output")
        
        return is_valid
    except Exception as e:
        print_step("File Content Validation Error", {"error": str(e)}, "error")
        return False

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components and keep only the filename
    sanitized = Path(filename).name
    
    # Remove any remaining dangerous characters
    sanitized = re.sub(r'[^\w\-_\.]', '_', sanitized)
    
    # Limit filename length
    if len(sanitized) > 255:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized

def validate_file_size(file_content: bytes, max_size: int) -> bool:
    """
    Validate file size is within limits.
    
    Args:
        file_content: File content as bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if file size is within limits
    """
    file_size = len(file_content)
    is_valid = file_size <= max_size
    
    print_step("File Size Validation", {
        "file_size": file_size,
        "max_size": max_size,
        "is_valid": is_valid
    }, "input" if is_valid else "error")
    
    return is_valid

def validate_uploaded_file(file_content: bytes, filename: str, allowed_types: list, max_size: int) -> dict:
    """
    Comprehensive file validation for uploads.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        allowed_types: List of allowed MIME types
        max_size: Maximum file size in bytes
        
    Returns:
        Validation result dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    print_step("File Upload Validation", {
        "filename": filename,
        "file_size": len(file_content),
        "allowed_types": allowed_types
    }, "input")
    
    # Validate file size
    if not validate_file_size(file_content, max_size):
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_size} bytes"
        )
    
    # Validate file content
    mime_type = magic.from_buffer(file_content, mime=True)
    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {mime_type}. Allowed types: {allowed_types}"
        )
    
    # Sanitize filename
    sanitized_filename = sanitize_filename(filename)
    
    result = {
        "original_filename": filename,
        "sanitized_filename": sanitized_filename,
        "mime_type": mime_type,
        "file_size": len(file_content),
        "is_valid": True
    }
    
    print_step("File Upload Validation", result, "output")
    return result

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
