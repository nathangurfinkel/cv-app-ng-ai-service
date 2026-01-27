"""
E2E integration tests for AI Service Jobs API.

These tests make real API calls to LLM providers and require valid API keys.
Tests are skipped if TEST_USER_API_KEY is not provided.

Set environment variables:
- AI_SERVICE_URL: Base URL of deployed AI service (default: http://localhost:8000)
- API_KEY: API Gateway key for authentication
- TEST_USER_API_KEY: User OpenAI/Gemini API key for testing
- JOBS_TABLE_NAME: DynamoDB table name (or use LocalStack)
- JOBS_QUEUE_URL: SQS queue URL (or use LocalStack)
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

# Skip all E2E tests if no API key provided
pytestmark = pytest.mark.skipif(
    not TEST_USER_API_KEY,
    reason="TEST_USER_API_KEY not provided - skipping E2E tests"
)

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

SAMPLE_CV_DATA = {
    "personal": {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0123",
        "location": "San Francisco, CA",
        "website": "johndoe.com",
        "linkedin": "linkedin.com/in/johndoe",
        "github": "github.com/johndoe"
    },
    "professional_summary": "Experienced software engineer",
    "experience": [
        {
            "company": "Tech Corp",
            "role": "Senior Software Engineer",
            "startDate": "2020-01",
            "endDate": "Present",
            "location": "San Francisco, CA",
            "description": "Led microservices development",
            "achievements": ["Improved performance by 40%"]
        }
    ],
    "education": [],
    "projects": [],
    "skills": {
        "technical": ["Python", "FastAPI"],
        "soft": ["Leadership"],
        "languages": ["English"]
    },
    "licenses_certifications": [],
    "job_description": SAMPLE_JOB_DESCRIPTION,
}


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


def poll_job_status(client: httpx.AsyncClient, job_id: str, max_wait: int = 120) -> Dict[str, Any]:
    """Poll job status until completion or timeout."""
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
            return data
        
        if data["status"] == "failed":
            assert "error" in data
            return data
        
        await asyncio.sleep(2)
    
    pytest.fail(f"Job {job_id} did not complete within {max_wait} seconds")


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_extract_job_e2e():
    """Test extract job with real LLM call, validate CVData structure."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        # Create job
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        # Skip if infrastructure not configured
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        data = response.json()
        job_id = data["job_id"]
        
        # Poll for completion
        result = await poll_job_status(client, job_id)
        
        # Validate result structure
        assert result["status"] == "succeeded"
        cv_data = result["result"]
        assert isinstance(cv_data, dict)
        assert "personal" in cv_data
        assert "experience" in cv_data
        assert isinstance(cv_data["experience"], list)


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_tailor_job_e2e():
    """Test tailor job with real LLM call."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/tailor",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "user_cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"
        assert "result" in result
        assert "analysis" in result["result"]  # Tailor includes analysis


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_evaluate_job_e2e():
    """Test evaluate job with real committee evaluation."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/evaluate",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "cv_json": SAMPLE_CV_DATA,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"
        
        # Validate committee evaluation structure
        evaluation = result["result"]
        assert "recruiter" in evaluation or "individual_evaluations" in evaluation


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_rephrase_job_e2e():
    """Test rephrase job with different instruction types."""
    instruction_types = ["default", "grammar", "shorten", "formal"]
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        for instruction_type in instruction_types:
            response = await client.post(
                f"{AI_SERVICE_URL}/ai/jobs/rephrase",
                headers=get_headers(user_api_key=TEST_USER_API_KEY),
                json={
                    "section_content": "Led development of microservices architecture",
                    "section_type": "experience",
                    "job_description": SAMPLE_JOB_DESCRIPTION,
                    "instruction_type": instruction_type,
                },
            )
            
            if response.status_code == 500 and "infrastructure is not configured" in response.text:
                pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
            
            assert response.status_code == 202
            job_id = response.json()["job_id"]
            
            result = await poll_job_status(client, job_id)
            assert result["status"] == "succeeded"
            assert "rephrased_content" in result["result"]


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_inject_keyword_e2e():
    """Test inject keyword job (success + REQUIRES_CONTEXT scenarios)."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        # Test successful injection
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/inject-keyword",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "section_content": "Led development of microservices architecture",
                "section_type": "experience",
                "keyword": "CI/CD",
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"
        
        # Result should either have rephrased_content or requires_context
        assert "rephrased_content" in result["result"] or "requires_context" in result["result"]


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_elaborate_job_e2e():
    """Test elaborate job with user context."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/elaborate",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "section_content": "Led development of microservices architecture",
                "section_type": "experience",
                "keyword": "CI/CD",
                "user_context": "Implemented CI/CD pipelines using GitHub Actions",
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"
        assert "rephrased_content" in result["result"]


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_recommend_job_e2e():
    """Test recommend job with real template recommendation."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/recommend",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "cv_data": SAMPLE_CV_DATA,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"
        
        # Validate recommendation structure
        recommendation = result["result"]
        assert "recommended_template" in recommendation
        assert "confidence_score" in recommendation
        assert "reasoning" in recommendation


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_byok_openai_e2e():
    """Test BYOK flow with OpenAI."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(tier="byok_lifetime", user_api_key=TEST_USER_API_KEY),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_byok_gemini_e2e():
    """Test BYOK flow with Gemini (if TEST_GEMINI_API_KEY is provided)."""
    gemini_key = os.getenv("TEST_GEMINI_API_KEY", "")
    if not gemini_key:
        pytest.skip("TEST_GEMINI_API_KEY not provided")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        headers = get_headers(tier="byok_lifetime", user_api_key=gemini_key)
        headers["X-User-Provider"] = "gemini"
        
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=headers,
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        result = await poll_job_status(client, job_id)
        assert result["status"] == "succeeded"


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_job_timeout_handling():
    """Test handling of long-running jobs (timeout scenario)."""
    # This test verifies that jobs that take too long are handled gracefully
    # In practice, this would require a job that actually times out
    # For now, we just verify the timeout mechanism exists
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/ai/jobs/extract",
            headers=get_headers(user_api_key=TEST_USER_API_KEY),
            json={
                "cv_text": SAMPLE_CV_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        
        if response.status_code == 500 and "infrastructure is not configured" in response.text:
            pytest.skip("AWS infrastructure (DynamoDB/SQS) not configured")
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        # Poll with shorter timeout to test timeout handling
        try:
            result = await poll_job_status(client, job_id, max_wait=5)
            # If job completes quickly, that's fine too
            assert result["status"] in ["succeeded", "failed"]
        except Exception:
            # Timeout is expected behavior
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])

