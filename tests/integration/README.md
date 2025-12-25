# Integration Tests

These tests make actual HTTP requests to deployed services to verify API contracts.

## Prerequisites

1. Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

2. Set environment variables:

**Option A: Export in your shell:**
```bash
export AI_SERVICE_URL="http://localhost:8000"  # or your deployed service URL
export API_KEY="test-key"  # Can be any value for local dev
export TEST_USER_API_KEY="sk-your-openai-api-key"  # Optional, for BYOK testing
export OPENAI_API_KEY="sk-your-openai-api-key"  # Required for roast endpoint
```

**Option B: Create `.env` file in project root:**
```bash
# Copy the example
cp .env.example .env

# Edit .env and add your keys:
# OPENAI_API_KEY=sk-your-key-here
# API_KEY=test-key
```

**Option C: Create `.env.test` in tests/integration/ directory:**
```bash
cd tests/integration
cp .env.test.example .env.test
# Edit .env.test with your test keys
```

## Running Tests

### Run all integration tests:
```bash
pytest tests/integration/ -v
```

### Run specific test file:
```bash
pytest tests/integration/test_jobs_api.py -v
pytest tests/integration/test_interview_api.py -v
pytest tests/integration/test_tier_gating.py -v
pytest tests/integration/test_roast_api.py -v
```

### Run specific test:
```bash
pytest tests/integration/test_jobs_api.py::test_create_extract_job -v
```

## Test Coverage

- **test_jobs_api.py**: Tests all job endpoints (extract, tailor, evaluate, rephrase, recommend)
- **test_interview_api.py**: Tests interview endpoints including SSE streaming
- **test_tier_gating.py**: Tests tier validation (FREE, BYOK, MANAGED)
- **test_roast_api.py**: Tests roast endpoint (free tier viral feature)

## Notes

- These tests require the AI service to be running (locally or deployed)
- Tests will fail if services are not accessible
- Tests use real API keys and make actual HTTP requests
- Some tests may take 1-2 minutes to complete (async job polling)

