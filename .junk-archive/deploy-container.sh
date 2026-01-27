#!/bin/bash

# Container-based deployment script for RAG stack
set -e

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
WORKER_FUNCTION_NAME="cv-builder-ai-worker"
AWS_REGION="eu-north-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="cv-builder-ai-service"
IMAGE_TAG="latest"
API_ID="${API_ID:-wz2lhr4qzk}" # existing API Gateway id in this account

# Resource names (configurable via env vars or defaults)
JOBS_TABLE_NAME="${JOBS_TABLE_NAME:-cv-builder-jobs}"
JOBS_QUEUE_NAME="${JOBS_QUEUE_NAME:-cv-builder-jobs-queue}"
DLQ_NAME="${DLQ_NAME:-cv-builder-jobs-dlq}"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo "Starting container-based deployment for AI service..."

# Build Docker image
echo "Building Docker image for linux/amd64 (Lambda)..."
# NOTE:
# - On Apple Silicon, use buildx + --load to avoid pushing an OCI image index (manifest list),
#   which Lambda may reject. We then `docker push` the loaded single-arch image.
if docker buildx version >/dev/null 2>&1; then
  docker buildx build --platform linux/amd64 --load -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
else
  docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
fi

# Tag for ECR
echo "Tagging image for ECR..."
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Push to ECR
echo "Pushing image to ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role"
echo "Ensuring Lambda function exists and uses packageType=Image..."

PACKAGE_TYPE=$(aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} --query 'Configuration.PackageType' --output text 2>/dev/null || echo "None")

if [ "${PACKAGE_TYPE}" = "Image" ]; then
  echo "Updating existing Image-based Lambda to new image..."
  aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --image-uri ${ECR_URI}:${IMAGE_TAG} \
    --region ${AWS_REGION} >/dev/null
else
  echo "Deleting existing non-Image Lambda (if any)..."
  aws lambda delete-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} 2>/dev/null || true
  echo "Waiting for deletion..."
  sleep 10

  echo "Creating new Lambda function with container image..."
  aws lambda create-function \
      --function-name ${FUNCTION_NAME} \
      --package-type Image \
      --code ImageUri=${ECR_URI}:${IMAGE_TAG} \
      --role ${ROLE_ARN} \
      --timeout 60 \
      --memory-size 1024 \
      --region ${AWS_REGION} \
      --environment Variables="{
          \"MOCK_PINECONE\": \"${MOCK_PINECONE:-false}\",
          \"PINECONE_API_KEY\": \"${PINECONE_API_KEY:-}\",
          \"OPENAI_API_KEY\": \"${OPENAI_API_KEY:-}\",
          \"VERBOSE\": \"${VERBOSE:-false}\",
          \"CORS_ORIGINS\": \"${CORS_ORIGINS:-https://main.d1z0zksl0bfdg3.amplifyapp.com}\",
          \"DEBUG\": \"${DEBUG:-false}\",
          \"JOBS_TABLE_NAME\": \"${JOBS_TABLE_NAME:-}\",
          \"JOBS_QUEUE_URL\": \"${JOBS_QUEUE_URL:-}\",
          \"LICENSE_SUBSCRIPTIONS_TABLE_NAME\": \"${LICENSE_SUBSCRIPTIONS_TABLE_NAME:-}\",
          \"LEMONSQUEEZY_WEBHOOK_SECRET\": \"${LEMONSQUEEZY_WEBHOOK_SECRET:-}\"
      }" >/dev/null
fi

# Update API Lambda environment variables if function already exists
if [ "${PACKAGE_TYPE}" = "Image" ]; then
  echo "Updating API Lambda environment variables..."
  aws lambda update-function-configuration \
      --function-name ${FUNCTION_NAME} \
      --environment Variables="{
          \"MOCK_PINECONE\": \"${MOCK_PINECONE:-false}\",
          \"PINECONE_API_KEY\": \"${PINECONE_API_KEY:-}\",
          \"OPENAI_API_KEY\": \"${OPENAI_API_KEY:-}\",
          \"VERBOSE\": \"${VERBOSE:-false}\",
          \"CORS_ORIGINS\": \"${CORS_ORIGINS:-https://main.d1z0zksl0bfdg3.amplifyapp.com}\",
          \"DEBUG\": \"${DEBUG:-false}\",
          \"JOBS_TABLE_NAME\": \"${JOBS_TABLE_NAME:-}\",
          \"JOBS_QUEUE_URL\": \"${JOBS_QUEUE_URL:-}\",
          \"LICENSE_SUBSCRIPTIONS_TABLE_NAME\": \"${LICENSE_SUBSCRIPTIONS_TABLE_NAME:-}\",
          \"LEMONSQUEEZY_WEBHOOK_SECRET\": \"${LEMONSQUEEZY_WEBHOOK_SECRET:-}\"
      }" \
      --region ${AWS_REGION} >/dev/null
fi

echo "Waiting for function to be active..."
aws lambda wait function-active --function-name ${FUNCTION_NAME} --region ${AWS_REGION}

echo "Updating worker Lambda (${WORKER_FUNCTION_NAME})..."
echo "NOTE: Worker Lambda uses handler 'app.worker.handler' (different from API Lambda's 'app.main.handler')"
WORKER_PACKAGE_TYPE=$(aws lambda get-function --function-name ${WORKER_FUNCTION_NAME} --region ${AWS_REGION} --query 'Configuration.PackageType' --output text 2>/dev/null || echo "None")
if [ "${WORKER_PACKAGE_TYPE}" = "Image" ]; then
  # Update worker Lambda code
  aws lambda update-function-code \
    --function-name ${WORKER_FUNCTION_NAME} \
    --image-uri ${ECR_URI}:${IMAGE_TAG} \
    --region ${AWS_REGION} >/dev/null
  aws lambda wait function-active --function-name ${WORKER_FUNCTION_NAME} --region ${AWS_REGION}
  
  # Configure worker Lambda handler and environment variables
  echo "Configuring worker Lambda handler and environment variables..."
  aws lambda update-function-configuration \
    --function-name ${WORKER_FUNCTION_NAME} \
    --handler app.worker.handler \
    --timeout 300 \
    --environment Variables="{
        \"JOBS_TABLE_NAME\": \"${JOBS_TABLE_NAME:-}\",
        \"JOBS_QUEUE_URL\": \"${JOBS_QUEUE_URL:-}\",
        \"OPENAI_API_KEY\": \"${OPENAI_API_KEY:-}\",
        \"JOB_TTL_HOURS\": \"${JOB_TTL_HOURS:-24}\",
        \"DEBUG\": \"${DEBUG:-false}\",
        \"VERBOSE\": \"${VERBOSE:-false}\"
    }" \
    --region ${AWS_REGION} >/dev/null
  aws lambda wait function-updated --function-name ${WORKER_FUNCTION_NAME} --region ${AWS_REGION}
else
  echo "Creating worker Lambda function..."
  aws lambda create-function \
    --function-name ${WORKER_FUNCTION_NAME} \
    --package-type Image \
    --code ImageUri=${ECR_URI}:${IMAGE_TAG} \
    --role ${ROLE_ARN} \
    --handler app.worker.handler \
    --timeout 300 \
    --memory-size 1024 \
    --region ${AWS_REGION} \
    --environment Variables="{
        \"JOBS_TABLE_NAME\": \"${JOBS_TABLE_NAME}\",
        \"JOBS_QUEUE_URL\": \"${JOBS_QUEUE_URL:-}\",
        \"OPENAI_API_KEY\": \"${OPENAI_API_KEY:-}\",
        \"JOB_TTL_HOURS\": \"${JOB_TTL_HOURS:-24}\",
        \"DEBUG\": \"${DEBUG:-false}\",
        \"VERBOSE\": \"${VERBOSE:-false}\"
    }" >/dev/null
  aws lambda wait function-active --function-name ${WORKER_FUNCTION_NAME} --region ${AWS_REGION}
  echo "✓ Worker Lambda created"
fi

echo "Ensuring API Gateway can invoke Lambda (API_ID=${API_ID})..."
aws lambda remove-permission \
  --function-name ${FUNCTION_NAME} \
  --statement-id apigateway-invoke \
  --region ${AWS_REGION} 2>/dev/null || true

aws lambda add-permission \
  --function-name ${FUNCTION_NAME} \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" \
  --region ${AWS_REGION} >/dev/null

# Set up SQS resources and DLQ
echo "Setting up SQS queue and Dead Letter Queue..."
QUEUE_URL=$(aws sqs get-queue-url --queue-name ${JOBS_QUEUE_NAME} --region ${AWS_REGION} --query 'QueueUrl' --output text 2>/dev/null || echo "")

if [ -z "$QUEUE_URL" ]; then
  echo "Creating SQS queue: ${JOBS_QUEUE_NAME}..."
  QUEUE_URL=$(aws sqs create-queue \
    --queue-name ${JOBS_QUEUE_NAME} \
    --attributes VisibilityTimeout=300 \
    --region ${AWS_REGION} \
    --query 'QueueUrl' \
    --output text)
  echo "✓ SQS queue created"
else
  echo "✓ SQS queue already exists"
fi

# Create DLQ
DLQ_URL=$(aws sqs get-queue-url --queue-name ${DLQ_NAME} --region ${AWS_REGION} --query 'QueueUrl' --output text 2>/dev/null || echo "")
if [ -z "$DLQ_URL" ]; then
  echo "Creating Dead Letter Queue: ${DLQ_NAME}..."
  DLQ_URL=$(aws sqs create-queue \
    --queue-name ${DLQ_NAME} \
    --region ${AWS_REGION} \
    --query 'QueueUrl' \
    --output text)
  echo "✓ DLQ created"
else
  echo "✓ DLQ already exists"
fi

# Get DLQ ARN
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url ${DLQ_URL} \
  --attribute-names QueueArn \
  --region ${AWS_REGION} \
  --query 'Attributes.QueueArn' \
  --output text)

# Attach DLQ to source queue (idempotent - update redrive policy)
echo "Attaching DLQ to source queue..."
aws sqs set-queue-attributes \
  --queue-url ${QUEUE_URL} \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"${DLQ_ARN}\\\",\\\"maxReceiveCount\\\":3}\"}" \
  --region ${AWS_REGION} >/dev/null
echo "✓ DLQ attached (maxReceiveCount=3)"

# Set up SQS event source mapping for worker Lambda
echo "Setting up SQS event source mapping for worker Lambda..."
QUEUE_ARN="arn:aws:sqs:${AWS_REGION}:${AWS_ACCOUNT_ID}:${JOBS_QUEUE_NAME}"

# Check if event source mapping already exists
ESM_UUID=$(aws lambda list-event-source-mappings \
  --function-name ${WORKER_FUNCTION_NAME} \
  --region ${AWS_REGION} \
  --query 'EventSourceMappings[?EventSourceArn==`'${QUEUE_ARN}'`].UUID' \
  --output text 2>/dev/null || echo "")

if [ -z "$ESM_UUID" ]; then
  echo "Creating SQS event source mapping..."
  aws lambda create-event-source-mapping \
    --function-name ${WORKER_FUNCTION_NAME} \
    --event-source-arn ${QUEUE_ARN} \
    --batch-size 1 \
    --maximum-batching-window-in-seconds 0 \
    --region ${AWS_REGION} >/dev/null
  echo "✓ Event source mapping created"
else
  echo "✓ Event source mapping already exists (UUID: ${ESM_UUID})"
  # Update existing mapping to ensure it's enabled
  aws lambda update-event-source-mapping \
    --uuid ${ESM_UUID} \
    --enabled \
    --region ${AWS_REGION} >/dev/null 2>&1 || true
fi

# Update JOBS_QUEUE_URL if not set (for worker Lambda env vars)
if [ -z "${JOBS_QUEUE_URL}" ]; then
  JOBS_QUEUE_URL="${QUEUE_URL}"
fi

# Update worker Lambda with correct queue URL if it changed
if [ "${WORKER_PACKAGE_TYPE}" = "Image" ]; then
  echo "Updating worker Lambda with queue URL..."
  aws lambda update-function-configuration \
    --function-name ${WORKER_FUNCTION_NAME} \
    --environment Variables="{
        \"JOBS_TABLE_NAME\": \"${JOBS_TABLE_NAME}\",
        \"JOBS_QUEUE_URL\": \"${JOBS_QUEUE_URL}\",
        \"OPENAI_API_KEY\": \"${OPENAI_API_KEY:-}\",
        \"JOB_TTL_HOURS\": \"${JOB_TTL_HOURS:-24}\",
        \"DEBUG\": \"${DEBUG:-false}\",
        \"VERBOSE\": \"${VERBOSE:-false}\"
    }" \
    --region ${AWS_REGION} >/dev/null
fi

echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo "Deployed Image: ${ECR_URI}:${IMAGE_TAG}"
echo "API Gateway URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
echo "SQS Queue: ${QUEUE_URL}"
echo "DLQ: ${DLQ_URL}"
echo "Worker Lambda: ${WORKER_FUNCTION_NAME}"
echo "=========================================="
