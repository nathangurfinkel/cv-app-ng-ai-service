# LocalStack vs Cloud Production Setup Comparison

Side-by-side comparison of local development (LocalStack) and production (AWS) setups.

## Overview

| Aspect | LocalStack (Dev) | Production (AWS) |
|--------|------------------|-------------------|
| **Purpose** | Local development and testing | Production deployment |
| **DynamoDB** | LocalStack emulation | Real AWS DynamoDB |
| **SQS** | LocalStack emulation | Real AWS SQS |
| **Worker** | Manual Python script | Lambda with SQS event source mapping |
| **Endpoint** | `http://localhost:4566` | Default AWS endpoints (empty) |
| **Setup** | Automated scripts | Manual/IaC |

## Infrastructure Comparison

### DynamoDB

| Feature | LocalStack | Production |
|---------|------------|------------|
| **Endpoint** | `http://localhost:4566` | `https://dynamodb.eu-north-1.amazonaws.com` |
| **Region** | `us-east-1` (default) | `eu-north-1` |
| **Tables** | `cv-builder-jobs`, `cv-builder-license-subscriptions` | Same table names |
| **Billing** | Free | PAY_PER_REQUEST |
| **Persistence** | `./localstack-data/` directory | AWS managed |
| **Setup** | `scripts/setup-localstack.sh` | Manual AWS CLI or IaC |

### SQS

| Feature | LocalStack | Production |
|---------|------------|------------|
| **Endpoint** | `http://localhost:4566` | `https://sqs.eu-north-1.amazonaws.com` |
| **Queue URL Format** | `http://localhost:4566/000000000000/cv-builder-jobs-queue` | `https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/cv-builder-jobs-queue` |
| **Region** | `us-east-1` (default) | `eu-north-1` |
| **Visibility Timeout** | 300 seconds | 300 seconds |
| **Setup** | `scripts/setup-localstack.sh` | Manual AWS CLI or IaC |

### Lambda Functions

| Feature | LocalStack | Production |
|---------|------------|------------|
| **API Lambda** | Not used (uvicorn server) | `cv-builder-ai-service` |
| **Worker Lambda** | `scripts/process-localstack-queue.py` | `cv-builder-ai-worker` |
| **Handler** | N/A (direct Python execution) | `app.main.handler` / `app.worker.handler` |
| **Trigger** | Manual HTTP requests | API Gateway (API) / SQS Event Source Mapping (Worker) |
| **Timeout** | N/A | 60s (API) / 300s (Worker) |

## Configuration Comparison

### Environment Variables

#### LocalStack (.env file)

```env
# AWS Infrastructure
JOBS_TABLE_NAME=cv-builder-jobs
JOBS_QUEUE_URL=http://localhost:4566/000000000000/cv-builder-jobs-queue
AWS_ENDPOINT_URL=http://localhost:4566
AWS_DEFAULT_REGION=us-east-1
LICENSE_SUBSCRIPTIONS_TABLE_NAME=cv-builder-license-subscriptions

# AI Services
OPENAI_API_KEY=your-key
PINECONE_API_KEY=your-key
MOCK_PINECONE=true

# CORS
CORS_ORIGINS=http://localhost:5173

# Debug
DEBUG=true
VERBOSE=true
```

#### Production (Lambda Environment Variables)

**API Lambda**:
```bash
JOBS_TABLE_NAME=cv-builder-jobs
JOBS_QUEUE_URL=https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/cv-builder-jobs-queue
AWS_ENDPOINT_URL=  # Empty (uses default AWS endpoints)
AWS_DEFAULT_REGION=eu-north-1
LICENSE_SUBSCRIPTIONS_TABLE_NAME=cv-builder-license-subscriptions

OPENAI_API_KEY=your-key
PINECONE_API_KEY=your-key
MOCK_PINECONE=false

CORS_ORIGINS=https://your-frontend-domain.com

DEBUG=false
VERBOSE=false
```

**Worker Lambda**:
```bash
JOBS_TABLE_NAME=cv-builder-jobs
JOBS_QUEUE_URL=https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/cv-builder-jobs-queue
AWS_ENDPOINT_URL=  # Empty
AWS_DEFAULT_REGION=eu-north-1

OPENAI_API_KEY=your-key  # For MANAGED tier only

JOB_TTL_HOURS=24
```

### Key Differences

1. **AWS_ENDPOINT_URL**: 
   - LocalStack: `http://localhost:4566`
   - Production: Empty (uses default AWS endpoints)

2. **Queue URL Format**:
   - LocalStack: `http://localhost:4566/000000000000/queue-name`
   - Production: `https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/queue-name`

3. **Region**:
   - LocalStack: `us-east-1` (default, can be changed)
   - Production: `eu-north-1` (Stockholm)

4. **MOCK_PINECONE**:
   - LocalStack: `true` (usually, for testing)
   - Production: `false` (use real Pinecone)

5. **CORS_ORIGINS**:
   - LocalStack: `http://localhost:5173` (dev frontend)
   - Production: `https://your-frontend-domain.com` (production frontend)

## Setup Steps Comparison

### LocalStack Setup

1. Start LocalStack: `./start-localstack.sh`
2. Set AWS CLI credentials (dummy): `export AWS_ACCESS_KEY_ID=test`
3. Run setup script: `./scripts/setup-localstack.sh`
4. Configure `.env` file with printed values
5. Start API server: `uvicorn app.main:app --reload`
6. Start worker script: `python3 scripts/process-localstack-queue.py`

**Time**: ~5 minutes

### Production Setup

1. Create DynamoDB tables (manual or IaC)
2. Create SQS queue (manual or IaC)
3. Build and push Docker image to ECR
4. Deploy API Lambda: `./deploy-container.sh`
5. Configure worker Lambda handler: `app.worker.handler`
6. Set worker Lambda environment variables
7. Create SQS event source mapping
8. Configure API Gateway integration
9. Set up IAM roles and permissions

**Time**: ~30-60 minutes (first time)

## Worker Processing Comparison

### LocalStack

- **Method**: Manual Python script (`process-localstack-queue.py`)
- **How it works**: 
  - Script polls SQS queue using boto3
  - Formats messages as Lambda SQS events
  - Calls `app.worker.handler` directly
  - Deletes messages after processing
- **Control**: Manual start/stop
- **Scaling**: Single process (manual)

### Production

- **Method**: Lambda with SQS event source mapping
- **How it works**:
  - AWS automatically triggers Lambda when messages arrive
  - Lambda processes messages in batches
  - AWS handles retries and DLQ
- **Control**: Automatic (managed by AWS)
- **Scaling**: Automatic (concurrent executions)

## Testing Comparison

### LocalStack

- **Speed**: Instant (no cold starts)
- **Cost**: Free
- **Isolation**: Local machine only
- **Debugging**: Full access to logs, breakpoints, local debugging
- **Reset**: Easy (`docker compose down -v`)

### Production

- **Speed**: Cold starts possible (first invocation)
- **Cost**: Pay per invocation + duration
- **Isolation**: AWS account
- **Debugging**: CloudWatch logs, X-Ray (if enabled)
- **Reset**: Manual cleanup of resources

## Data Persistence

### LocalStack

- **Location**: `./localstack-data/` directory
- **Persistence**: Survives container restarts
- **Backup**: Git-ignore, manual backup if needed
- **Reset**: Delete directory to start fresh

### Production

- **Location**: AWS managed (DynamoDB, SQS)
- **Persistence**: Permanent (until deleted)
- **Backup**: AWS backup services, point-in-time recovery
- **Reset**: Manual deletion via AWS CLI/console

## Common Issues and Solutions

### Issue: Queue URL Format Mismatch

**LocalStack**: Uses `http://localhost:4566/...` format
**Production**: Uses `https://sqs.eu-north-1.amazonaws.com/...` format

**Solution**: Environment variable `JOBS_QUEUE_URL` must match the environment.

### Issue: Endpoint URL Configuration

**LocalStack**: Must set `AWS_ENDPOINT_URL=http://localhost:4566`
**Production**: Must leave `AWS_ENDPOINT_URL` empty (or unset)

**Solution**: Use different `.env` files or environment-specific configuration.

### Issue: Worker Not Processing

**LocalStack**: Worker script must be running manually
**Production**: SQS event source mapping must be configured

**Solution**: 
- LocalStack: Check `process-localstack-queue.py` is running
- Production: Verify event source mapping exists and is enabled

## Migration Path

When moving from LocalStack to Production:

1. **Create AWS Resources**: DynamoDB tables, SQS queue
2. **Update Environment Variables**: Change `AWS_ENDPOINT_URL` to empty, update queue URL format
3. **Deploy Lambda Functions**: Use deployment script
4. **Configure Event Source Mapping**: Set up SQS → Worker Lambda trigger
5. **Test**: Verify end-to-end flow works in production

## Best Practices

### LocalStack

- Use separate `.env.local` file for local development
- Keep LocalStack data directory in `.gitignore`
- Document any LocalStack-specific quirks
- Test async job flow before deploying

### Production

- Use Infrastructure as Code (IaC) for resources
- Store secrets in AWS Secrets Manager
- Set up CloudWatch alarms
- Configure DLQ for worker failures
- Use separate AWS accounts for staging/production

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [LOCALSTACK_SETUP.md](LOCALSTACK_SETUP.md) - Local development setup
- [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) - Production deployment guide

