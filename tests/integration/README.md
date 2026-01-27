# Integration Tests

This directory contains integration tests organized into two tiers:

1. **Mocked Tests** (Fast, CI/CD) - No real API calls, uses mocked LLM providers
2. **E2E Tests** (Comprehensive, Pre-Deployment) - Real API calls with actual LLM providers

## Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

This includes:
- `pytest>=7.4.0` - Test framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-mock>=3.11.0` - Mocking utilities
- `moto>=4.2.0` - AWS service mocking (for DynamoDB/SQS)
- `httpx>=0.24.0` - HTTP client for E2E tests

2. Set environment variables:

**For Mocked Tests (no API keys needed):**
```bash
# Optional - only if testing with LocalStack
export AWS_ENDPOINT_URL="http://localhost:4566"
export JOBS_TABLE_NAME="test-jobs-table"
export JOBS_QUEUE_URL="http://localhost:4566/000000000000/test-jobs-queue"
```

**For E2E Tests (requires API keys):**
```bash
export AI_SERVICE_URL="http://localhost:8000"  # or your deployed service URL
export API_KEY="test-key"  # Can be any value for local dev
export TEST_USER_API_KEY="sk-your-openai-api-key"  # Required for E2E tests
export OPENAI_API_KEY="sk-your-openai-api-key"  # Required for roast endpoint
export JOBS_TABLE_NAME="cv-builder-jobs"  # DynamoDB table name
export JOBS_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789/test-queue"  # SQS queue URL
```

## Running Tests

### Fast CI/CD Tests (Mocked)

Run all mocked tests (fast, no API calls):
```bash
pytest tests/integration/test_jobs_api_mocked.py -v -m "mocked"
```

Run cross-repo contract tests:
```bash
pytest tests/integration/test_cross_repo_contract.py -v -m "mocked"
```

**Expected Duration**: < 30 seconds total

### Comprehensive E2E Tests (Real APIs)

Run all E2E tests (requires TEST_USER_API_KEY):
```bash
pytest tests/integration/test_jobs_api_e2e.py -v -m "e2e"
```

Run all existing E2E tests:
```bash
pytest tests/integration/test_jobs_api.py -v
pytest tests/integration/test_interview_api.py -v
pytest tests/integration/test_tier_gating.py -v
pytest tests/integration/test_roast_api.py -v
```

**Expected Duration**: 5-10 minutes total

### Run All Tests

Run both mocked and E2E tests (E2E will skip if no API key):
```bash
pytest tests/integration/ -v
```

### Run Specific Test

```bash
pytest tests/integration/test_jobs_api_mocked.py::test_create_extract_job_mocked -v
pytest tests/integration/test_jobs_api_e2e.py::test_extract_job_e2e -v
```

## Test Organization

### Mocked Tests (`test_jobs_api_mocked.py`)

- **Purpose**: Fast tests for CI/CD pipeline
- **Characteristics**: 
  - No real API calls (mocked LLM providers)
  - Uses moto for DynamoDB/SQS mocking
  - Fast execution (< 5 seconds per test)
- **Test Cases**:
  - Job creation with mocked LLM
  - Job status transitions
  - BYOK headers passed to worker
  - Tier validation
  - Error handling
  - Job cancellation
  - All job types

### E2E Tests (`test_jobs_api_e2e.py`)

- **Purpose**: Comprehensive validation before production deployments
- **Characteristics**:
  - Real API calls (requires valid API keys)
  - Real AWS infrastructure (or LocalStack with real LLM)
  - Slower execution (30-120 seconds per test)
- **Test Cases**:
  - Extract job with real LLM
  - Tailor job with real LLM
  - Evaluate job with real committee
  - Rephrase job with different instruction types
  - Inject keyword (success + REQUIRES_CONTEXT)
  - Elaborate job with user context
  - Template recommendation
  - BYOK with OpenAI
  - BYOK with Gemini
  - Job timeout handling

### Cross-Repo Contract Tests (`test_cross_repo_contract.py`)

- **Purpose**: Validate API contracts match between frontend and backend
- **Test Cases**:
  - Job creation request/response shapes
  - Job status response format
  - Error format validation
  - CV data transformation
  - Polling compatibility

## Test Coverage

### Job Endpoints
- ✅ Extract CV data
- ✅ Tailor CV
- ✅ Evaluate CV
- ✅ Rephrase section
- ✅ Inject keyword
- ✅ Elaborate with keyword
- ✅ Template recommendation

### Other Endpoints
- ✅ Interview API (test_interview_api.py)
- ✅ Tier gating (test_tier_gating.py)
- ✅ Roast API (test_roast_api.py)

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.mocked` - Mocked tests (fast, no API calls)
- `@pytest.mark.e2e` - E2E tests (real API calls)
- `@pytest.mark.slow` - Tests that take > 30 seconds

Filter tests by marker:
```bash
pytest -m "mocked"  # Run only mocked tests
pytest -m "e2e"     # Run only E2E tests
pytest -m "not slow"  # Skip slow tests
```

## Notes

### Mocked Tests
- No API keys required
- No real AWS infrastructure needed (uses moto)
- Fast execution suitable for CI/CD
- Tests job lifecycle and error handling without real LLM calls

### E2E Tests
- Require `TEST_USER_API_KEY` environment variable
- Require AI service to be running (locally or deployed)
- Require AWS infrastructure (DynamoDB + SQS) or LocalStack
- Tests will skip automatically if API key not provided
- Some tests may take 1-2 minutes to complete (async job polling)

### Local Development
- Use LocalStack for local DynamoDB/SQS: `docker-compose -f docker-compose.localstack.yml up`
- Run worker manually: `python scripts/process-localstack-queue.py`
- See [LOCALSTACK_SETUP.md](../docs/LOCALSTACK_SETUP.md) for details

