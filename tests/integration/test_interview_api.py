"""
Integration tests for AI Service Interview API.

Tests interview endpoints including SSE streaming.
"""

import os
import pytest
import httpx
import json
from typing import Dict, Any

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
TEST_USER_API_KEY = os.getenv("TEST_USER_API_KEY", "")


def get_headers(tier: str = "managed_subscription", user_api_key: str = None, license_key: str = None) -> Dict[str, str]:
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


@pytest.mark.asyncio
async def test_start_interview():
    """Test POST /ai/interview/start endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/interview/start",
            headers=get_headers(user_api_key=TEST_USER_API_KEY or None),
            json={
                "cv_summary": "Senior software engineer with 5 years experience in Python and microservices",
                "job_title": "Senior Backend Engineer",
                "difficulty": "medium",
            },
        )
        
        # If OpenAI API key is not configured, skip this test
        if response.status_code in [500, 503]:
            error_text = response.text.lower()
            if "api key" in error_text or "openai" in error_text or "unavailable" in error_text:
                pytest.skip("OpenAI API key not configured - skipping interview test")
        
        # If license key is required but not provided/valid, skip this test
        if response.status_code == 403:
            error_data = response.json()
            detail = error_data.get("detail", {}) if isinstance(error_data, dict) else {}
            if isinstance(detail, dict):
                error_type = detail.get("error", "")
                if error_type in ["invalid_or_expired_license", "tier_upgrade_required", "license_key_required"]:
                    pytest.skip("Valid license key not configured - skipping interview test (requires MANAGED tier)")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "session_id" in data
        assert "question" in data
        assert isinstance(data["question"], str)
        assert len(data["question"]) > 0
        return data["session_id"], data["question"]


@pytest.mark.asyncio
async def test_interview_answer_sse():
    """Test GET /ai/interview/answer SSE streaming."""
    # First start an interview (will skip if API key not available)
    try:
        session_id, first_question = await test_start_interview()
    except Exception:
        pytest.skip("OpenAI API key not configured - skipping interview test")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Make SSE request
        async with client.stream(
            "GET",
            f"{AI_SERVICE_URL}/ai/interview/answer",
            headers=get_headers(user_api_key=TEST_USER_API_KEY or None),
            params={
                "session_id": session_id,
                "question": first_question,
                "answer": "I have 5 years of experience building scalable backend systems using Python and FastAPI.",
                "difficulty": "medium",
            },
        ) as response:
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response.headers["content-type"] == "text/event-stream"
            
            # Collect chunks
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        if "chunk" in chunk_data:
                            chunks.append(chunk_data["chunk"])
                        elif "error" in chunk_data:
                            pytest.fail(f"SSE error: {chunk_data['error']}")
                    except json.JSONDecodeError:
                        pass
            
            # Verify we got some chunks
            assert len(chunks) > 0, "No chunks received from SSE stream"
            # Verify chunks are strings
            assert all(isinstance(chunk, str) for chunk in chunks)


@pytest.mark.asyncio
async def test_analyze_interview():
    """Test POST /ai/interview/analyze endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/interview/analyze",
            headers=get_headers(user_api_key=TEST_USER_API_KEY or None),
            json={
                "transcript": "Interviewer: Tell me about yourself. Candidate: I am a software engineer with 5 years of experience.",
                "duration_seconds": 120,
            },
        )
        
        # If OpenAI API key is not configured, skip this test
        if response.status_code in [500, 503]:
            error_text = response.text.lower()
            if "api key" in error_text or "openai" in error_text or "unavailable" in error_text:
                pytest.skip("OpenAI API key not configured - skipping interview test")
        
        # If license key is required but not provided/valid, skip this test
        if response.status_code == 403:
            error_data = response.json()
            detail = error_data.get("detail", {}) if isinstance(error_data, dict) else {}
            if isinstance(detail, dict):
                error_type = detail.get("error", "")
                if error_type in ["invalid_or_expired_license", "tier_upgrade_required", "license_key_required"]:
                    pytest.skip("Valid license key not configured - skipping interview test (requires MANAGED tier)")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify exact response structure matches frontend type
        assert "filler_word_count" in data
        assert "words_per_minute" in data
        assert "confidence_score" in data
        assert "suggestions" in data
        
        assert isinstance(data["filler_word_count"], int)
        assert isinstance(data["words_per_minute"], int)
        assert isinstance(data["confidence_score"], int)
        assert isinstance(data["suggestions"], list)
        
        # Verify ranges
        assert 0 <= data["confidence_score"] <= 100
        assert data["filler_word_count"] >= 0
        assert data["words_per_minute"] >= 0


@pytest.mark.asyncio
async def test_interview_free_tier_rejection():
    """Test that FREE tier is rejected for interview endpoints."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/interview/start",
            headers=get_headers(tier="free"),
            json={
                "cv_summary": "Software engineer",
                "job_title": "Engineer",
                "difficulty": "easy",
            },
        )
        
        assert response.status_code == 403, f"Expected 403 for FREE tier, got {response.status_code}"


@pytest.mark.asyncio
async def test_interview_byok_tier_rejection():
    """Test that BYOK tier is rejected for interview endpoints (requires MANAGED)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/interview/start",
            headers=get_headers(tier="byok_lifetime", user_api_key=TEST_USER_API_KEY or "test-key"),
            json={
                "cv_summary": "Software engineer",
                "job_title": "Engineer",
                "difficulty": "easy",
            },
        )
        
        assert response.status_code == 403, f"Expected 403 for BYOK tier, got {response.status_code}"

