# Cloud Deployment Guide

Complete guide for deploying the CV Builder AI Service to AWS Lambda (production).

## Overview

The service consists of two Lambda functions:
1. **API Lambda** (`cv-builder-ai-service`) - Handles HTTP requests via API Gateway
2. **Worker Lambda** (`cv-builder-ai-worker`) - Processes async jobs from SQS queue

Both functions use the same container image but different handlers.

## Prerequisites

- AWS CLI installed and configured
- Docker installed (for building container image)
- AWS account with appropriate permissions:
  - Lambda (create/update functions)
  - ECR (push images)
  - DynamoDB (create tables)
  - SQS (create queues)
  - API Gateway (configure integrations)
  - IAM (create/update roles)

## Quick Start

### 1. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-key"
export PINECONE_API_KEY="your-pinecone-key"  # optional
export CORS_ORIGINS="https://your-frontend-domain.com"
export JOBS_TABLE_NAME="cv-builder-jobs"
export JOBS_QUEUE_URL="https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/cv-builder-jobs-queue"
export LICENSE_SUBSCRIPTIONS_TABLE_NAME="cv-builder-license-subscriptions"
export LEMONSQUEEZY_WEBHOOK_SECRET="your-webhook-secret"
```

### 2. Create AWS Resources

#### DynamoDB Tables

```bash
# Jobs table
aws dynamodb create-table \
  --table-name cv-builder-jobs \
  --attribute-definitions AttributeName=job_id,AttributeType=S \
  --key-schema AttributeName=job_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-north-1

# License subscriptions table
aws dynamodb create-table \
  --table-name cv-builder-license-subscriptions \
  --attribute-definitions AttributeName=subscription_id,AttributeType=S \
  --key-schema AttributeName=subscription_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-north-1
```

#### SQS Queue

```bash
aws sqs create-queue \
  --queue-name cv-builder-jobs-queue \
  --attributes VisibilityTimeout=300 \
  --region eu-north-1
```

Get the queue URL:
```bash
aws sqs get-queue-url \
  --queue-name cv-builder-jobs-queue \
  --region eu-north-1 \
  --query 'QueueUrl' \
  --output text
```

### 3. Deploy Lambda Functions

Use the automated deployment script:

```bash
./deploy-container.sh
```

This script automatically:
- Builds Docker image for Linux/amd64
- Pushes to ECR
- Creates/updates API Lambda function
- Creates/updates Worker Lambda function
- Configures API Gateway permissions
- Creates SQS queue (if not exists)
- Creates Dead Letter Queue (DLQ) and attaches it
- Creates/updates SQS event source mapping for worker Lambda

**Note**: The deployment script fully automates infrastructure setup. No manual steps required.

## Detailed Deployment

### Step 1: Build and Push Container Image

The deployment script handles this automatically, but manual steps:

```bash
# Build image
docker buildx build --platform linux/amd64 --load -t cv-builder-ai-service:latest .

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.eu-north-1.amazonaws.com/cv-builder-ai-service"

# Tag for ECR
docker tag cv-builder-ai-service:latest ${ECR_URI}:latest

# Login to ECR
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin ${ECR_URI}

# Create ECR repository (if not exists)
aws ecr create-repository \
  --repository-name cv-builder-ai-service \
  --region eu-north-1 \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null || true

# Push image
docker push ${ECR_URI}:latest
```

### Step 2: Deploy API Lambda

The deployment script creates/updates the API Lambda with:

- **Function Name**: `cv-builder-ai-service`
- **Handler**: `app.main.handler` (configured via Dockerfile CMD)
- **Runtime**: Container image
- **Memory**: 1024 MB
- **Timeout**: 60 seconds
- **Environment Variables**: See [Environment Variables](#environment-variables) section

### Step 3: Deploy Worker Lambda

The deployment script creates/updates the worker Lambda with:

- **Function Name**: `cv-builder-ai-worker`
- **Handler**: `app.worker.handler` (must be set via function configuration)
- **Runtime**: Container image (same as API Lambda)
- **Memory**: 1024 MB
- **Timeout**: 300 seconds (5 minutes, matches SQS visibility timeout)
- **Environment Variables**: See [Environment Variables](#environment-variables) section

**Important**: The worker Lambda handler must be explicitly set because the Dockerfile CMD defaults to `app.main.handler`. Set it via:

```bash
aws lambda update-function-configuration \
  --function-name cv-builder-ai-worker \
  --handler app.worker.handler \
  --region eu-north-1
```

### Step 4: Configure SQS Event Source Mapping

Create the event source mapping to trigger the worker Lambda:

```bash
QUEUE_ARN="arn:aws:sqs:eu-north-1:${AWS_ACCOUNT_ID}:cv-builder-jobs-queue"

aws lambda create-event-source-mapping \
  --function-name cv-builder-ai-worker \
  --event-source-arn ${QUEUE_ARN} \
  --batch-size 1 \
  --maximum-batching-window-in-seconds 0 \
  --region eu-north-1
```

**Configuration**:
- **Batch Size**: 1 (process one message at a time)
- **Batching Window**: 0 (process immediately)
- **Visibility Timeout**: 300 seconds (must match Lambda timeout)

### Step 5: Configure API Gateway

The deployment script configures API Gateway permissions. Ensure your API Gateway is set up:

- **Type**: HTTP API (or REST API)
- **Integration**: Lambda proxy integration
- **Route**: `ANY /{proxy+}` → `cv-builder-ai-service` Lambda
- **Stage**: `prod` (or your stage name)

### Step 6: Dead Letter Queue (Automated)

The deployment script automatically creates and configures a Dead Letter Queue (DLQ):
- **DLQ Name**: `cv-builder-jobs-dlq` (configurable via `DLQ_NAME` env var)
- **Max Receive Count**: 3 (messages retry 3 times before moving to DLQ)
- **Automatic Attachment**: DLQ is automatically attached to the source queue

No manual setup required. The DLQ prevents infinite retry loops and helps identify problematic messages.

## Environment Variables

### API Lambda (`cv-builder-ai-service`)

Required:
```bash
OPENAI_API_KEY=<your-key>
CORS_ORIGINS=https://your-frontend-domain.com
```

Optional:
```bash
PINECONE_API_KEY=<your-key>
MOCK_PINECONE=false
DEBUG=false
VERBOSE=false
```

### Worker Lambda (`cv-builder-ai-worker`)

Required:
```bash
JOBS_TABLE_NAME=cv-builder-jobs
JOBS_QUEUE_URL=https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/cv-builder-jobs-queue
OPENAI_API_KEY=<your-key>  # For MANAGED tier only
```

Optional:
```bash
JOB_TTL_HOURS=24
DEBUG=false
VERBOSE=false
```

**Note**: The deployment script currently sets environment variables for the API Lambda only. You must manually set them for the worker Lambda:

```bash
aws lambda update-function-configuration \
  --function-name cv-builder-ai-worker \
  --environment Variables="{
    \"JOBS_TABLE_NAME\":\"cv-builder-jobs\",
    \"JOBS_QUEUE_URL\":\"https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/cv-builder-jobs-queue\",
    \"OPENAI_API_KEY\":\"your-key\",
    \"JOB_TTL_HOURS\":\"24\"
  }" \
  --region eu-north-1
```

## IAM Roles and Permissions

### Lambda Execution Role

Both Lambdas need a role with:

**Basic Permissions**:
- `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

**API Lambda Additional Permissions**:
- DynamoDB: Read/Write to `cv-builder-jobs` table
- SQS: SendMessage to `cv-builder-jobs-queue`
- DynamoDB: Read/Write to `cv-builder-license-subscriptions` table (for license validation)

**Worker Lambda Additional Permissions**:
- DynamoDB: Read/Write to `cv-builder-jobs` table
- SQS: ReceiveMessage, DeleteMessage, GetQueueAttributes on `cv-builder-jobs-queue`

**Example Policy** (attach to Lambda execution role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:eu-north-1:ACCOUNT_ID:table/cv-builder-jobs",
        "arn:aws:dynamodb:eu-north-1:ACCOUNT_ID:table/cv-builder-license-subscriptions"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:eu-north-1:ACCOUNT_ID:cv-builder-jobs-queue"
    }
  ]
}
```

## Monitoring

### CloudWatch Logs

- **API Lambda**: `/aws/lambda/cv-builder-ai-service`
- **Worker Lambda**: `/aws/lambda/cv-builder-ai-worker`

### CloudWatch Metrics

- **Lambda**: Invocations, Duration, Errors, Throttles
- **DynamoDB**: Read/Write capacity, Throttles
- **SQS**: ApproximateNumberOfMessages, ApproximateNumberOfMessagesVisible

### Alarms (Recommended)

Set up CloudWatch alarms for:
- Lambda errors > threshold
- SQS queue depth > threshold
- Lambda duration approaching timeout

## Troubleshooting

### Worker Not Processing Jobs

**Symptoms**: Jobs stay in `queued` status

**Check**:
1. SQS event source mapping exists and is enabled
2. Worker Lambda has correct handler (`app.worker.handler`)
3. Worker Lambda has environment variables set (`JOBS_TABLE_NAME`, `JOBS_QUEUE_URL`)
4. Worker Lambda has IAM permissions for DynamoDB and SQS
5. Worker Lambda timeout (300s) matches SQS visibility timeout

**Debug**:
```bash
# Check event source mapping
aws lambda list-event-source-mappings \
  --function-name cv-builder-ai-worker \
  --region eu-north-1

# Check worker Lambda configuration
aws lambda get-function-configuration \
  --function-name cv-builder-ai-worker \
  --region eu-north-1

# Check CloudWatch logs
aws logs tail /aws/lambda/cv-builder-ai-worker --follow --region eu-north-1
```

### API Lambda Timeout

**Symptoms**: Requests timeout after 60 seconds

**Solutions**:
- Increase timeout (max 15 minutes for API Gateway)
- Optimize AI service calls
- Use async jobs for long-running operations (already implemented)

### SQS Messages Not Visible

**Symptoms**: Messages stuck in queue, worker not receiving them

**Check**:
- SQS visibility timeout matches worker Lambda timeout
- Event source mapping is enabled
- Worker Lambda is not throttled

## Cost Optimization

- **Lambda Memory**: 1024 MB is a balance. Consider testing lower values.
- **DynamoDB**: PAY_PER_REQUEST mode (no capacity planning, pay per request)
- **SQS**: Pay per request (very cheap)
- **Container Image**: Use ECR lifecycle policies to clean up old images

## Security Best Practices

1. **Environment Variables**: Store secrets in AWS Secrets Manager, not environment variables
2. **IAM Roles**: Use least privilege principle
3. **VPC**: Consider VPC for Lambda if accessing private resources
4. **API Keys**: Rotate regularly
5. **CORS**: Restrict to frontend domain only

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [LOCALSTACK_SETUP.md](LOCALSTACK_SETUP.md) - Local development setup
- [SETUP_COMPARISON.md](SETUP_COMPARISON.md) - Dev vs Production comparison

