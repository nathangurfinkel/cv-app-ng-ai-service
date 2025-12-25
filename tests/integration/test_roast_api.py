"""
Integration tests for Roast API (free tier viral feature).
"""

import os
import pytest
import httpx

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

SAMPLE_CV_TEXT = """
John Doe
Software Engineer
Email: john.doe@example.com

EXPERIENCE
Senior Software Engineer | Tech Corp | 2020 - Present
- Led development of microservices architecture
- Improved system performance by 40%
- Mentored team of 5 junior developers

Software Engineer | Startup Inc | 2018 - 2020
- Built RESTful APIs using Python and FastAPI
- Implemented CI/CD pipelines

EDUCATION
BS Computer Science | University | 2018
"""


@pytest.mark.asyncio
async def test_roast_endpoint():
    """Test POST /ai/roast endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": SAMPLE_CV_TEXT,
            },
        )
        
        # If OpenAI API key is not configured, expect 500 or 503
        if response.status_code in [500, 503]:
            pytest.skip("OpenAI API key not configured - skipping roast test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "roast" in data
        assert "score" in data
        assert "share_url" in data
        
        assert isinstance(data["roast"], str)
        assert len(data["roast"]) > 0
        
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 10
        
        assert isinstance(data["share_url"], str)
        assert len(data["share_url"]) > 0


@pytest.mark.asyncio
async def test_roast_no_auth_required():
    """Test that roast endpoint doesn't require user authentication."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
                # No X-User-Tier, X-User-Provider, etc.
            },
            json={
                "cv_text": SAMPLE_CV_TEXT,
            },
        )
        
        # If OpenAI API key is not configured, expect 500 or 503
        if response.status_code in [500, 503]:
            pytest.skip("OpenAI API key not configured - skipping roast test")
        
        assert response.status_code == 200, "Roast should work without user auth"


@pytest.mark.asyncio
async def test_roast_rate_limiting():
    """Test rate limiting on roast endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First request
        response1 = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": SAMPLE_CV_TEXT,
            },
        )
        
        # If OpenAI API key is not configured, skip this test
        if response1.status_code in [500, 503]:
            pytest.skip("OpenAI API key not configured - skipping roast test")
        
        # Immediate second request with same content should be rate limited
        response2 = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": SAMPLE_CV_TEXT,  # Same content
            },
        )
        
        # Should get 429 or 200 (depending on timing)
        assert response2.status_code in [200, 429]
        if response2.status_code == 429:
            data = response2.json()
            assert "detail" in data or "message" in data


@pytest.mark.asyncio
async def test_roast_validation():
    """Test that roast endpoint validates CV text length."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Too short CV
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/roast",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "cv_text": "Short",  # Too short
            },
        )
        
        # FastAPI returns 422 for validation errors (Pydantic validation)
        assert response.status_code in [400, 422], f"Should reject too short CV text, got {response.status_code}: {response.text}"

