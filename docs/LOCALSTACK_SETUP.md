# LocalStack Setup Guide

Complete guide for setting up LocalStack for local development of the CV Builder AI Service.

## Overview

LocalStack emulates AWS services (DynamoDB, SQS) locally, allowing you to develop and test async job functionality without deploying to AWS.

## Prerequisites

- Docker Desktop installed and running
- AWS CLI installed (credentials can be dummy for LocalStack)
- Python 3.13+ (for running the worker script)

## Quick Start

### 1. Start LocalStack

Use the provided startup script:

```bash
./start-localstack.sh
```

Or manually:

```bash
docker compose -f docker-compose.localstack.yml up -d
```

Wait 10-15 seconds for LocalStack to be ready. Check health:

```bash
curl http://localhost:4566/_localstack/health
```

### 2. Set Up AWS CLI Credentials (for LocalStack)

LocalStack accepts any credentials, but they must be set:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Create LocalStack Resources

Run the setup script:

```bash
./scripts/setup-localstack.sh
```

This creates:
- DynamoDB table: `cv-builder-jobs`
- SQS queue: `cv-builder-jobs-queue`
- DynamoDB table: `cv-builder-license-subscriptions` (for licensing)

### 4. Configure Environment Variables

Add the following to your `.env` file (values printed by setup script):

```env
# AWS Infrastructure (LocalStack)
JOBS_TABLE_NAME=cv-builder-jobs
JOBS_QUEUE_URL=http://localhost:4566/000000000000/cv-builder-jobs-queue
AWS_ENDPOINT_URL=http://localhost:4566
AWS_DEFAULT_REGION=us-east-1

# License Subscriptions Table (for LemonSqueezy webhooks)
LICENSE_SUBSCRIPTIONS_TABLE_NAME=cv-builder-license-subscriptions
```

### 5. Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start the Worker (in separate terminal)

The worker script simulates the SQS event source mapping that triggers the worker Lambda in production:

```bash
python3 scripts/process-localstack-queue.py
```

Keep this running while testing async job endpoints.

## Detailed Setup

### LocalStack Services

The `docker-compose.localstack.yml` configures:

- **Port**: `4566` (LocalStack Gateway)
- **Services**: DynamoDB, SQS
- **Region**: `us-east-1` (default)
- **Data Persistence**: `./localstack-data` (persists between restarts)

### DynamoDB Tables

#### Jobs Table (`cv-builder-jobs`)

**Schema**:
- **Partition Key**: `job_id` (String)
- **Attributes**:
  - `job_type` (String)
  - `status` (String: queued, processing, succeeded, failed, cancelled)
  - `created_at` (Number, Unix timestamp)
  - `updated_at` (Number, Unix timestamp)
  - `ttl` (Number, Unix timestamp for auto-deletion)
  - `result` (Map, optional)
  - `error_code` (String, optional)
  - `error_message` (String, optional)

**Billing Mode**: PAY_PER_REQUEST (no capacity planning needed)

#### License Subscriptions Table (`cv-builder-license-subscriptions`)

**Schema**:
- **Partition Key**: `subscription_id` (String, LemonSqueezy subscription ID)
- **Attributes**:
  - `user_id` (String, optional)
  - `license_key` (String)
  - `tier` (String: managed_subscription, etc.)
  - `status` (String: active, cancelled, expired)
  - `created_at` (Number, Unix timestamp)
  - `updated_at` (Number, Unix timestamp)
  - `expires_at` (Number, Unix timestamp, optional)

**Billing Mode**: PAY_PER_REQUEST

### SQS Queue

#### Jobs Queue (`cv-builder-jobs-queue`)

**Configuration**:
- **Visibility Timeout**: 300 seconds (5 minutes)
- **Message Retention**: 4 days (default)
- **Queue URL Format**: `http://localhost:4566/000000000000/cv-builder-jobs-queue`

**Message Format**:
```json
{
  "job_id": "uuid",
  "job_type": "extract|tailor|evaluate|rephrase|recommend|inject_keyword|elaborate",
  "payload": {
    "cv_text": "...",
    "job_description": "..."
  },
  "user_provider": "openai|gemini",
  "user_api_key": "...",
  "user_tier": "byok_lifetime|managed_subscription|..."
}
```

## Testing Async Jobs

### 1. Create a Job

```bash
curl -X POST http://localhost:8000/ai/jobs/extract \
  -H "Content-Type: application/json" \
  -H "X-User-Tier: byok_lifetime" \
  -H "X-User-Provider: openai" \
  -H "X-User-Api-Key: your-api-key" \
  -d '{
    "cv_text": "John Doe\nSoftware Engineer\n...",
    "job_description": "Looking for a senior developer..."
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### 2. Check Job Status

```bash
curl http://localhost:8000/ai/jobs/{job_id}
```

Response (when completed):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "result": {
    "personal_info": {...},
    "experience": [...],
    "education": [...]
  }
}
```

### 3. Monitor Worker Processing

Watch the worker terminal for processing logs:

```
Polling queue: http://localhost:4566/000000000000/cv-builder-jobs-queue
Processing message: abc123...
✓ Processed successfully: {'processed': 1}
✓ Deleted message from queue
```

## End-to-End Testing

Use the provided test script:

```bash
./scripts/test-e2e-flow.sh
```

This script:
1. Creates an extract job
2. Polls job status until completion
3. Displays the result

**Note**: Requires a valid OpenAI API key in `.env` for full E2E test. Without it, the test verifies infrastructure flow (job creation → enqueue → worker processing) but AI processing will fail.

## Troubleshooting

### LocalStack Not Starting

**Issue**: Docker container fails to start

**Solutions**:
- Check Docker Desktop is running
- Check port 4566 is not in use: `lsof -i :4566`
- View logs: `docker compose -f docker-compose.localstack.yml logs`

### Resources Not Found

**Issue**: `ResourceNotFoundException` when accessing DynamoDB/SQS

**Solutions**:
- Verify resources exist: `aws dynamodb list-tables --endpoint-url http://localhost:4566`
- Re-run setup script: `./scripts/setup-localstack.sh`
- Check `AWS_ENDPOINT_URL` is set in `.env`

### Worker Not Processing Jobs

**Issue**: Jobs stay in `queued` status

**Solutions**:
- Verify worker script is running: `ps aux | grep process-localstack-queue`
- Check queue has messages: `aws sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/cv-builder-jobs-queue --attribute-names ApproximateNumberOfMessages --endpoint-url http://localhost:4566`
- Check worker logs for errors
- Verify `JOBS_QUEUE_URL` and `JOBS_TABLE_NAME` in `.env`

### Queue URL Format Issues

**Issue**: Queue URL uses `sqs.us-east-1.localhost.localstack.cloud` instead of `localhost`

**Solution**: The setup script normalizes the URL automatically. If you see the wrong format, re-run the setup script.

## Stopping LocalStack

```bash
docker compose -f docker-compose.localstack.yml down
```

**Note**: Data in `./localstack-data` persists. To start fresh:

```bash
docker compose -f docker-compose.localstack.yml down -v
rm -rf localstack-data
```

## Data Persistence

LocalStack data is stored in `./localstack-data/`:
- DynamoDB tables and data
- SQS queues and messages (until TTL)
- LocalStack state

This allows you to restart LocalStack without losing test data.

## Differences from Production

| Aspect | LocalStack (Dev) | Production (AWS) |
|--------|------------------|------------------|
| DynamoDB | Emulated on `localhost:4566` | Real AWS DynamoDB |
| SQS | Emulated on `localhost:4566` | Real AWS SQS |
| Worker | Manual script (`process-localstack-queue.py`) | Lambda with SQS event source mapping |
| Endpoint URL | `http://localhost:4566` | Empty (default AWS endpoints) |
| Queue URL | `http://localhost:4566/...` | `https://sqs.eu-north-1.amazonaws.com/...` |

See [SETUP_COMPARISON.md](SETUP_COMPARISON.md) for detailed comparison.

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) - Production deployment guide
- [SETUP_COMPARISON.md](SETUP_COMPARISON.md) - Dev vs Production comparison

