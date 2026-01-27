# AI Service Architecture

## Overview

The CV Builder AI Service uses a **dual-Lambda architecture** to handle both synchronous API requests and asynchronous job processing. This design separates concerns and allows for independent scaling of API and worker components.

## Architecture Diagram

```
┌─────────────┐
│   Client    │
│  (Frontend) │
└──────┬──────┘
       │ HTTP/HTTPS
       │
       ▼
┌─────────────────────────────────────┐
│         API Gateway                  │
│    (HTTP API, API Key Auth)          │
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Lambda: cv-builder-ai-service    │
│   Handler: app.main.handler         │
│   (FastAPI + Mangum)                │
└──────┬──────────────────────────────┘
       │
       ├───► Synchronous endpoints (direct response)
       │     - /health
       │     - /ai/cv/tailor (sync)
       │     - /ai/evaluation/cv
       │
       └───► Async job creation
             │
             ├───► Create job record in DynamoDB
             │     (metadata only, no payload)
             │
             └───► Send message to SQS
                   (includes payload + BYOK headers)
                         │
                         ▼
              ┌──────────────────────┐
              │   SQS Queue          │
              │   (Job messages)     │
              └──────────┬───────────┘
                         │
                         │ Event Source Mapping
                         │ (automatic trigger)
                         ▼
              ┌──────────────────────┐
              │ Lambda:              │
              │ cv-builder-ai-worker │
              │ Handler:             │
              │ app.worker.handler   │
              └──────────┬───────────┘
                         │
                         ├───► Read job from DynamoDB
                         ├───► Process with AI service
                         │     (extract, tailor, evaluate, etc.)
                         └───► Update job status in DynamoDB
                               (succeeded/failed with result)
```

## Entry Points

### 1. API Handler (`app/main.py`)

**Purpose**: Handle HTTP requests from API Gateway

**Handler**: `app.main.handler` (Mangum adapter wrapping FastAPI app)

**Lambda Function**: `cv-builder-ai-service`

**Invocation**: API Gateway → Lambda (synchronous)

**Responsibilities**:
- Serve FastAPI routes (health checks, CV operations, evaluation)
- Create async jobs (extract, tailor, evaluate, rephrase, recommend)
- Handle BYOK (Bring Your Own Key) authentication headers
- Validate tier-based access control

**Key Components**:
- FastAPI application with CORS middleware
- Router modules for different feature areas
- Mangum adapter for Lambda compatibility

### 2. Worker Handler (`app/worker.py`)

**Purpose**: Process async jobs from SQS queue

**Handler**: `app.worker.handler` (SQS event handler)

**Lambda Function**: `cv-builder-ai-worker`

**Invocation**: SQS Event Source Mapping → Lambda (automatic)

**Responsibilities**:
- Poll SQS queue (via event source mapping)
- Process job payloads (CV text, job descriptions)
- Call AI services (OpenAI/Gemini via BYOK or system key)
- Update job status in DynamoDB
- Handle errors and retries

**Key Components**:
- SQS event parser
- Job type router (extract, tailor, evaluate, etc.)
- AI service integration
- DynamoDB repository for job state

### 3. Local Dev Worker (`scripts/process-localstack-queue.py`)

**Purpose**: Simulate SQS event source mapping for local development

**Usage**: Manual script run in separate terminal

**How it works**:
- Polls LocalStack SQS queue using boto3
- Formats messages as Lambda SQS events
- Calls `app.worker.handler` directly
- Deletes messages after successful processing

## Data Flow

### Synchronous Request Flow

1. Client → API Gateway → Lambda (`cv-builder-ai-service`)
2. FastAPI route handler processes request
3. Direct response returned to client
4. No DynamoDB or SQS involved

### Asynchronous Job Flow

1. **Job Creation**:
   - Client → API Gateway → Lambda (`cv-builder-ai-service`)
   - Route handler validates request and extracts BYOK headers
   - `JobsService.create_*_job()` called
   - Job metadata written to DynamoDB (status: `queued`)
   - Job payload + BYOK headers sent to SQS queue
   - Response: `202 Accepted` with `job_id`

2. **Job Processing**:
   - SQS event source mapping triggers Lambda (`cv-builder-ai-worker`)
   - Worker handler receives SQS event with job message
   - Worker reads job metadata from DynamoDB
   - Worker extracts payload and BYOK headers from SQS message
   - Worker creates AI service with user's API key (or system key for MANAGED tier)
   - Worker processes job (calls AI service)
   - Worker updates DynamoDB with result (status: `succeeded` or `failed`)

3. **Job Status Polling**:
   - Client polls `/ai/jobs/{job_id}` endpoint
   - API Lambda reads from DynamoDB
   - Returns current status and result (if completed)

## Key Design Decisions

### 1. Dual-Lambda Architecture

**Why**: Separates API concerns from background processing
- API Lambda: Fast response times, handles HTTP
- Worker Lambda: Long-running tasks, handles SQS events
- Independent scaling and timeout configuration

### 2. Payload in SQS, Not DynamoDB

**Why**: Privacy and data sovereignty
- CV text and job descriptions are sensitive (PII)
- SQS messages are ephemeral (TTL-based retention)
- DynamoDB only stores job metadata and results
- Aligns with local-first vault plan (`local-first_vault_c7381a99`)

### 3. BYOK (Bring Your Own Key) Support

**Why**: User data sovereignty and cost control
- Users provide their own OpenAI/Gemini API keys
- System key only used for verified MANAGED tier subscriptions
- Keys passed via HTTP headers, stored in SQS message (ephemeral)
- Never logged or persisted

### 4. Single Docker Image, Dual Handlers

**Why**: Code reuse and simpler deployment
- Same image contains both API and worker code
- Lambda function configuration determines which handler to use
- `CMD` in Dockerfile sets default (API handler)
- Worker Lambda overrides handler via function configuration

## Infrastructure Components

### DynamoDB

**Table**: `cv-builder-jobs` (or configured name)

**Schema**:
- `job_id` (String, Partition Key)
- `job_type` (String)
- `status` (String: queued, processing, succeeded, failed, cancelled)
- `created_at` (Number, Unix timestamp)
- `updated_at` (Number, Unix timestamp)
- `ttl` (Number, Unix timestamp for auto-deletion)
- `result` (Map, optional, job output)
- `error_code` (String, optional)
- `error_message` (String, optional)

**TTL**: Jobs auto-delete after configured hours (default: 24)

### SQS

**Queue**: `cv-builder-jobs-queue` (or configured name)

**Message Format**:
```json
{
  "job_id": "uuid",
  "job_type": "extract|tailor|evaluate|...",
  "payload": {
    "cv_text": "...",
    "job_description": "..."
  },
  "user_provider": "openai|gemini",
  "user_api_key": "...",
  "user_tier": "byok_lifetime|managed_subscription|..."
}
```

**Visibility Timeout**: 300 seconds (5 minutes)
- Prevents other workers from processing same message
- Should be >= worker Lambda timeout

### Lambda Functions

#### API Lambda (`cv-builder-ai-service`)

- **Runtime**: Python 3.13 (container image)
- **Handler**: `app.main.handler`
- **Memory**: 1024 MB
- **Timeout**: 60 seconds
- **Trigger**: API Gateway (HTTP API)
- **Environment Variables**: CORS origins, API keys, debug flags

#### Worker Lambda (`cv-builder-ai-worker`)

- **Runtime**: Python 3.13 (container image)
- **Handler**: `app.worker.handler`
- **Memory**: 1024 MB
- **Timeout**: 300 seconds (5 minutes, matches SQS visibility timeout)
- **Trigger**: SQS Event Source Mapping
- **Environment Variables**: DynamoDB table name, SQS queue URL, API keys

## Local Development vs Production

### Local Development (LocalStack)

- **DynamoDB**: LocalStack emulation on `localhost:4566`
- **SQS**: LocalStack emulation on `localhost:4566`
- **Worker**: Manual script (`process-localstack-queue.py`) instead of Lambda
- **Endpoint URL**: `http://localhost:4566` (configured via `AWS_ENDPOINT_URL`)

### Production (AWS)

- **DynamoDB**: Real AWS DynamoDB table
- **SQS**: Real AWS SQS queue
- **Worker**: Lambda with SQS event source mapping (automatic)
- **Endpoint URL**: Empty (uses default AWS endpoints)

See [SETUP_COMPARISON.md](SETUP_COMPARISON.md) for detailed differences.

## Security Considerations

1. **No PII in Logs**: CV text and job descriptions never logged
2. **Ephemeral Payloads**: Sensitive data only in SQS (TTL-based cleanup)
3. **BYOK Isolation**: User API keys never stored, only passed through
4. **Tier Validation**: Server-side validation of user tiers before processing
5. **CORS Restrictions**: Production CORS limited to frontend domain

## Monitoring

- **API Lambda**: CloudWatch logs, API Gateway metrics
- **Worker Lambda**: CloudWatch logs, SQS metrics (DLQ for failures)
- **DynamoDB**: CloudWatch metrics (read/write capacity, throttles)
- **SQS**: CloudWatch metrics (message count, visibility timeout)

## Related Documentation

- [LOCALSTACK_SETUP.md](LOCALSTACK_SETUP.md) - Local development setup
- [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) - Production deployment guide
- [SETUP_COMPARISON.md](SETUP_COMPARISON.md) - Dev vs Production comparison

