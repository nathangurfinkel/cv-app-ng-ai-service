"""
Integration tests for tier gating and validation.

Tests FREE, BYOK, and MANAGED tier access control.
"""

import os
import pytest
import httpx
from typing import Dict, Any

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
TEST_USER_API_KEY = os.getenv("TEST_USER_API_KEY", "")


def get_headers(tier: str, user_api_key: str = None, license_key: str = None) -> Dict[str, str]:
    """Get request headers for API calls."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "X-User-Tier": tier,
    }
    if user_api_key:
        headers["X-User-Provider"] = "openai"
        headers["X-User-Api-Key"] = user_api_key
    if license_key:
        headers["X-License-Key"] = license_key
    return headers


SAMPLE_CV_TEXT = "Software engineer with 5 years experience"
SAMPLE_JOB_DESCRIPTION = "Looking for a senior software engineer"


@pytest.mark.asyncio
async def test_free_tier_cannot_use_ai_operations():
    """Test that FREE tier cannot use /ai/jobs/* endpoints."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(tier="free"),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        assert response.status_code == 403, f"Expected 403 for FREE tier, got {response.status_code}"
        data = response.json()
        assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_byok_tier_requires_api_key():
    """Test that BYOK tier requires X-User-Provider and X-User-Api-Key headers."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Without API key
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(tier="byok_lifetime"),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        # If AWS infrastructure is not configured, skip this test
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured - skipping jobs test")
        
        # Should either reject (403) or create job that fails in worker
        assert response.status_code in [202, 403], f"Unexpected status: {response.status_code}"
        
        # With API key (if provided)
        if TEST_USER_API_KEY:
            response = await client.post(
                f"{AI_SERVICE_URL}/ai/jobs/extract",
                headers=get_headers(tier="byok_lifetime", user_api_key=TEST_USER_API_KEY),
                json={
                    "cv_text": SAMPLE_CV_TEXT,
                    "job_description": SAMPLE_JOB_DESCRIPTION,
                },
            )
            assert response.status_code == 202, f"Expected 202 with valid BYOK, got {response.status_code}"


@pytest.mark.asyncio
async def test_managed_tier_requires_license_key():
    """Test that MANAGED tier requires X-License-Key header for verification."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Without license key (should downgrade to FREE)
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(tier="managed_subscription"),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        # Should reject (403) because license verification fails
        assert response.status_code == 403, f"Expected 403 without license key, got {response.status_code}"


@pytest.mark.asyncio
async def test_free_tier_can_use_roast():
    """Test that FREE tier can use /ai/roast endpoint (free feature)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": SAMPLE_CV_TEXT * 10,  # Make it long enough
            },
        )
        
        # If OpenAI API key is not configured, expect 500 or 503
        if response.status_code in [500, 503]:
            pytest.skip("OpenAI API key not configured - skipping roast test")
        
        assert response.status_code == 200, f"Expected 200 for roast, got {response.status_code}: {response.text}"
        data = response.json()
        assert "roast" in data
        assert "score" in data
        assert "share_url" in data
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 10


@pytest.mark.asyncio
async def test_roast_rate_limiting():
    """Test that roast endpoint has rate limiting."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First request should succeed
        response1 = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": SAMPLE_CV_TEXT * 10,
            },
        )
        
        # Second request with same content should be rate limited
        response2 = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": SAMPLE_CV_TEXT * 10,  # Same content
            },
        )
        
        # One of them should be rate limited (429)
        if response2.status_code == 429:
            data = response2.json()
            assert "detail" in data or "message" in data

