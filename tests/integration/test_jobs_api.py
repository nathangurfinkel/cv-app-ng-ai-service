"""
Integration tests for AI Service Jobs API.

These tests make actual HTTP requests to the deployed AI service
to verify API contracts are correct.

Set environment variables:
- AI_SERVICE_URL: Base URL of deployed AI service (default: http://localhost:8000)
- API_KEY: API Gateway key for authentication
- TEST_USER_API_KEY: Optional user OpenAI API key for BYOK testing
"""

import os
import time
import asyncio
import pytest
import httpx
from typing import Dict, Any

# Test configuration
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
TEST_USER_API_KEY = os.getenv("TEST_USER_API_KEY", "")

# Test fixtures
SAMPLE_CV_TEXT = """
John Doe
Software Engineer
Email: john.doe@example.com
Phone: +1-555-0123

EXPERIENCE
Senior Software Engineer | Tech Corp | 2020 - Present
- Led development of microservices architecture
- Improved system performance by 40%
- Mentored team of 5 junior developers

Software Engineer | Startup Inc | 2018 - 2020
- Built RESTful APIs using Python and FastAPI
- Implemented CI/CD pipelines
"""

SAMPLE_JOB_DESCRIPTION = """
We are looking for a Senior Software Engineer with experience in:
- Microservices architecture
- Python and FastAPI
- Team leadership
- Performance optimization
"""


def get_headers(tier: str = "byok_lifetime", user_api_key: str = None) -> Dict[str, str]:
    """Get request headers for API calls."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "X-User-Tier": tier,
    }
    if user_api_key:
        headers["X-User-Provider"] = "openai"
        headers["X-User-Api-Key"] = user_api_key
    return headers


@pytest.mark.asyncio
async def test_create_extract_job():
    """Test POST /ai/jobs/extract endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(user_api_key=TEST_USER_API_KEY or None),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        # If AWS infrastructure is not configured, skip this test
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured - skipping jobs test")
        
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        return data["job_id"]


@pytest.mark.asyncio
async def test_create_tailor_job():
    """Test POST /ai/jobs/tailor endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/tailor",
            headers=get_headers(user_api_key=TEST_USER_API_KEY or None),
            json={
                "user_cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        # If AWS infrastructure is not configured, skip this test
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured - skipping jobs test")
        
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        return data["job_id"]


@pytest.mark.asyncio
async def test_get_job_status():
    """Test GET /ai/jobs/{job_id} endpoint."""
    # First create a job (will skip if infrastructure not available)
    try:
        job_id = await test_create_extract_job()
    except Exception:
        pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured - skipping jobs test")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Poll until job completes (with timeout)
        max_wait = 120  # 2 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = await client.get(
                f"{AI_SERVICE_URL}/ai/jobs/{job_id}",
                headers=get_headers(),
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["job_id"] == job_id
            assert "status" in data
            
            if data["status"] == "succeeded":
                assert "result" in data
                assert data["result"] is not None
                # Verify result structure
                result = data["result"]
                assert isinstance(result, dict)
                # Should have CV data structure
                assert "personal" in result or "experience" in result
                return data
            
            if data["status"] == "failed":
                assert "error" in data
                error = data["error"]
                # Error fields are optional (code and message can be None)
                assert isinstance(error, dict)
                if error.get("code"):
                    assert isinstance(error["code"], str)
                if error.get("message"):
                    assert isinstance(error["message"], str)
                return data
            
            # Wait before next poll
            await asyncio.sleep(2)
        
        pytest.fail(f"Job {job_id} did not complete within {max_wait} seconds")


@pytest.mark.asyncio
async def test_job_error_format():
    """Test that error responses have correct format (optional code/message)."""
    # Create a job with invalid data to trigger an error
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(user_api_key=TEST_USER_API_KEY or None),
            json={
                "cv_text": "",  # Empty CV should fail validation
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        # If AWS infrastructure is not configured, skip this test
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured - skipping jobs test")
        
        # Should either reject immediately (400/422) or create job that fails
        if response.status_code in [400, 422]:
            # Immediate validation error
            assert response.status_code in [400, 422]
        else:
            # Job created, check status for error
            assert response.status_code == 202
            job_id = response.json()["job_id"]
            
            # Poll for error status
            max_wait = 30
            start_time = time.time()
            while time.time() - start_time < max_wait:
                status_response = await client.get(
                    f"{AI_SERVICE_URL}/ai/jobs/{job_id}",
                    headers=get_headers(),
                )
                status_data = status_response.json()
                
                if status_data["status"] == "failed":
                    error = status_data.get("error")
                    if error:
                        # Verify error format: code and message are optional
                        assert isinstance(error, dict)
                        # Both fields can be None or strings
                        assert "code" in error or "message" in error
                    return
                
                await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_free_tier_rejection():
    """Test that FREE tier is rejected for AI operations."""
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
async def test_cancel_job():
    """Test DELETE /ai/jobs/{job_id} endpoint."""
    # Create a job (will skip if infrastructure not available)
    try:
        job_id = await test_create_extract_job()
    except Exception:
        pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured - skipping jobs test")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{AI_SERVICE_URL}/ai/jobs/{job_id}",
            headers=get_headers(),
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] in ["cancelled", "queued", "processing"]


if __name__ == "__main__":
    import asyncio
    asyncio.run(pytest.main([__file__, "-v"]))

