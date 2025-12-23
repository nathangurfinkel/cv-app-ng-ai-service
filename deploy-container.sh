#!/bin/bash

# Container-based deployment script for RAG stack
set -e

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
AWS_REGION="eu-north-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="cv-builder-ai-service"
IMAGE_TAG="latest"
API_ID="${API_ID:-wz2lhr4qzk}" # existing API Gateway id in this account

echo "📋 AWS Account ID: $AWS_ACCOUNT_ID"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo "🚀 Starting container-based deployment for AI service..."

# Build Docker image
echo "📦 Building Docker image for linux/amd64 (Lambda)..."
# NOTE:
# - On Apple Silicon, use buildx + --load to avoid pushing an OCI image index (manifest list),
#   which Lambda may reject. We then `docker push` the loaded single-arch image.
if docker buildx version >/dev/null 2>&1; then
  docker buildx build --platform linux/amd64 --load -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
else
  docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
fi

# Tag for ECR
echo "🏷️ Tagging image for ECR..."
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Push to ECR
echo "📤 Pushing image to ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role"
echo "🔧 Ensuring Lambda function exists and uses packageType=Image..."

PACKAGE_TYPE=$(aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} --query 'Configuration.PackageType' --output text 2>/dev/null || echo "None")

if [ "${PACKAGE_TYPE}" = "Image" ]; then
  echo "🔄 Updating existing Image-based Lambda to new image..."
  aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --image-uri ${ECR_URI}:${IMAGE_TAG} \
    --region ${AWS_REGION} >/dev/null
else
  echo "🗑️ Deleting existing non-Image Lambda (if any)..."
  aws lambda delete-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} 2>/dev/null || true
  echo "⏳ Waiting for deletion..."
  sleep 10

  echo "🆕 Creating new Lambda function with container image..."
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
          \"DEBUG\": \"${DEBUG:-false}\"
      }" >/dev/null
fi

echo "⏳ Waiting for function to be active..."
aws lambda wait function-active --function-name ${FUNCTION_NAME} --region ${AWS_REGION}

echo "🔐 Ensuring API Gateway can invoke Lambda (API_ID=${API_ID})..."
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

echo "🧪 Testing the deployment..."
echo "✅ Deployed Image: ${ECR_URI}:${IMAGE_TAG}"
echo "✅ API Gateway URL (existing): https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
