#!/bin/bash
# End-to-end test script for local async job flow

set -e

API_URL="http://localhost:8000"
SAMPLE_CV_TEXT="John Doe
Software Engineer
Email: john.doe@example.com
Phone: +1-555-123-4567

EXPERIENCE
Senior Software Engineer | Tech Corp | Jan 2020 - Present
- Led development of microservices architecture
- Improved system performance by 40%
- Mentored junior developers

Software Engineer | Startup Inc | Jun 2018 - Dec 2019
- Built RESTful APIs using Python and FastAPI
- Implemented CI/CD pipelines
- Reduced deployment time by 50%

EDUCATION
BS Computer Science | University of Technology | 2014 - 2018
GPA: 3.8/4.0

SKILLS
- Python, JavaScript, TypeScript
- AWS, Docker, Kubernetes
- FastAPI, React, Node.js"

echo "=========================================="
echo "Testing End-to-End Async Job Flow"
echo "=========================================="
echo ""

# Step 1: Create extract job
echo "Step 1: Creating extract job..."
# Use python to properly escape JSON
PAYLOAD=$(python3 -c "
import json
import sys
cv_text = '''${SAMPLE_CV_TEXT}'''
payload = {'cv_text': cv_text, 'job_description': ''}
print(json.dumps(payload))
")

# For local testing, use BYOK tier (requires X-User-Tier header)
# Load API key from .env if available
if [ -f .env ]; then
  export $(grep -E "^OPENAI_API_KEY=" .env | xargs)
fi

# Use real API key if available, otherwise use test-key (will fail but tests the flow)
API_KEY="${OPENAI_API_KEY:-test-key}"
if [ "${API_KEY}" == "test-key" ]; then
  echo "⚠️  Warning: Using test API key. Job will fail at AI processing step."
  echo "   Set OPENAI_API_KEY in .env for full E2E test."
fi

JOB_RESPONSE=$(curl -s -X POST "${API_URL}/ai/jobs/extract" \
  -H "Content-Type: application/json" \
  -H "X-User-Tier: byok_lifetime" \
  -H "X-User-Provider: openai" \
  -H "X-User-Api-Key: ${API_KEY}" \
  -d "${PAYLOAD}")

echo "Response: ${JOB_RESPONSE}"
JOB_ID=$(echo "${JOB_RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null || echo "")

if [ -z "${JOB_ID}" ]; then
  echo "❌ Failed to create job"
  exit 1
fi

echo "✓ Job created with ID: ${JOB_ID}"
echo ""

# Step 2: Poll job status
echo "Step 2: Polling job status (max 60 seconds)..."
MAX_ATTEMPTS=30
ATTEMPT=0
STATUS="queued"

while [ "${STATUS}" != "succeeded" ] && [ "${STATUS}" != "failed" ] && [ ${ATTEMPT} -lt ${MAX_ATTEMPTS} ]; do
  sleep 2
  ATTEMPT=$((ATTEMPT + 1))
  
  STATUS_RESPONSE=$(curl -s "${API_URL}/ai/jobs/${JOB_ID}")
  STATUS=$(echo "${STATUS_RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
  
  echo "[${ATTEMPT}/${MAX_ATTEMPTS}] Status: ${STATUS}"
  
  if [ "${STATUS}" == "succeeded" ]; then
    echo ""
    echo "✓ Job completed successfully!"
    echo ""
    echo "Result preview:"
    echo "${STATUS_RESPONSE}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('result', {}), indent=2))" 2>/dev/null | head -30
    echo ""
    echo "=========================================="
    echo "✅ End-to-end test PASSED"
    echo "=========================================="
    exit 0
  elif [ "${STATUS}" == "failed" ]; then
    echo ""
    ERROR_MSG=$(echo "${STATUS_RESPONSE}" | python3 -c "import sys, json; data=json.load(sys.stdin); err=data.get('error', {}); print(err.get('message', 'Unknown error'))" 2>/dev/null)
    if echo "${ERROR_MSG}" | grep -q "API key"; then
      echo "⚠️  Job failed due to invalid API key (expected in test mode)"
      echo "   Error: ${ERROR_MSG}"
      echo ""
      echo "✅ Flow test PASSED (job creation → enqueue → worker processing → status update)"
      echo "   Note: AI processing failed due to test API key, but infrastructure works correctly"
      echo ""
      echo "=========================================="
      echo "✅ End-to-end infrastructure test PASSED"
      echo "=========================================="
      exit 0
    else
      echo "❌ Job failed with unexpected error"
      echo "${STATUS_RESPONSE}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('error', {}), indent=2))" 2>/dev/null
      exit 1
    fi
  fi
done

if [ ${ATTEMPT} -ge ${MAX_ATTEMPTS} ]; then
  echo ""
  echo "❌ Test timed out - job did not complete in time"
  echo "Final status: ${STATUS}"
  exit 1
fi

