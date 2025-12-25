#!/bin/bash
# Setup script for LocalStack resources (DynamoDB table and SQS queue)

set -e

LOCALSTACK_ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "Setting up LocalStack resources..."
echo "Endpoint: $LOCALSTACK_ENDPOINT"
echo "Region: $AWS_REGION"
echo ""

# DynamoDB Table for Jobs
TABLE_NAME="cv-builder-jobs"
echo "Creating DynamoDB table: $TABLE_NAME"
aws dynamodb create-table \
  --endpoint-url "$LOCALSTACK_ENDPOINT" \
  --region "$AWS_REGION" \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=job_id,AttributeType=S \
  --key-schema \
    AttributeName=job_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --no-cli-pager || echo "Table may already exist"

echo "✓ DynamoDB table created"
echo ""

# SQS Queue for Jobs
QUEUE_NAME="cv-builder-jobs-queue"
echo "Creating SQS queue: $QUEUE_NAME"
QUEUE_URL_RAW=$(aws sqs create-queue \
  --endpoint-url "$LOCALSTACK_ENDPOINT" \
  --region "$AWS_REGION" \
  --queue-name "$QUEUE_NAME" \
  --attributes VisibilityTimeout=300 \
  --no-cli-pager \
  --query 'QueueUrl' \
  --output text 2>/dev/null || aws sqs get-queue-url \
    --endpoint-url "$LOCALSTACK_ENDPOINT" \
    --region "$AWS_REGION" \
    --queue-name "$QUEUE_NAME" \
    --no-cli-pager \
    --query 'QueueUrl' \
    --output text)

# Normalize queue URL to use localhost format for better compatibility
# Convert: http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/queue-name
# To: http://localhost:4566/000000000000/queue-name
QUEUE_URL=$(echo "$QUEUE_URL_RAW" | sed 's|http://sqs\.us-east-1\.localhost\.localstack\.cloud:4566|http://localhost:4566|g' || echo "$QUEUE_URL_RAW")

echo "✓ SQS queue created: $QUEUE_URL"
echo ""

echo "=========================================="
echo "LocalStack setup complete!"
echo "=========================================="
echo ""
echo "Add these to your .env file:"
echo "JOBS_TABLE_NAME=$TABLE_NAME"
echo "JOBS_QUEUE_URL=$QUEUE_URL"
echo "AWS_ENDPOINT_URL=$LOCALSTACK_ENDPOINT"
echo "AWS_DEFAULT_REGION=$AWS_REGION"
echo ""

