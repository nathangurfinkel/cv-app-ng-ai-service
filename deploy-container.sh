#!/bin/bash

# Container-based deployment script for RAG stack
set -e

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
AWS_REGION="eu-north-1"
AWS_ACCOUNT_ID="303774815769"
ECR_REPOSITORY="cv-builder-ai-service"
IMAGE_TAG="latest"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo "🚀 Starting container-based deployment for RAG stack..."

# Build Docker image
echo "📦 Building Docker image with multi-stage build..."
docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .

# Tag for ECR
echo "🏷️ Tagging image for ECR..."
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Push to ECR
echo "📤 Pushing image to ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

# Delete existing function if it exists
echo "🗑️ Deleting existing Lambda function..."
if aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
    aws lambda delete-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION}
    echo "⏳ Waiting for function deletion..."
    sleep 10
fi

# Create Lambda function
echo "🚀 Creating new Lambda function with container image..."
aws lambda create-function \
    --function-name ${FUNCTION_NAME} \
    --package-type Image \
    --code ImageUri=${ECR_URI}:${IMAGE_TAG} \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role \
    --timeout 30 \
    --memory-size 1024 \
    --region ${AWS_REGION} \
    --environment Variables='{
        "MOCK_PINECONE": "false",
        "PINECONE_API_KEY": "'${PINECONE_API_KEY}'",
        "OPENAI_API_KEY": "'${OPENAI_API_KEY}'",
        "VERBOSE": "false",
        "CORS_ORIGINS": "'${CORS_ORIGINS:-https://main.d3q8q8q8q8q8q8.amplifyapp.com}'",
        "DEBUG": "false"
    }'

echo "⏳ Waiting for function to be active..."
aws lambda wait function-active --function-name ${FUNCTION_NAME} --region ${AWS_REGION}

echo "🌐 Creating API Gateway..."
API_ID=$(aws apigateway create-rest-api \
    --name ${FUNCTION_NAME}-api \
    --description "API Gateway for ${FUNCTION_NAME}" \
    --region ${AWS_REGION} \
    --query 'id' \
    --output text)

echo "📋 API Gateway ID: ${API_ID}"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id ${API_ID} \
    --region ${AWS_REGION} \
    --query 'items[0].id' \
    --output text)

# Create proxy resource
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id ${API_ID} \
    --parent-id ${ROOT_RESOURCE_ID} \
    --path-part '{proxy+}' \
    --region ${AWS_REGION} \
    --query 'id' \
    --output text)

# Create ANY method
aws apigateway put-method \
    --rest-api-id ${API_ID} \
    --resource-id ${PROXY_RESOURCE_ID} \
    --http-method ANY \
    --authorization-type NONE \
    --region ${AWS_REGION}

# Create integration
aws apigateway put-integration \
    --rest-api-id ${API_ID} \
    --resource-id ${PROXY_RESOURCE_ID} \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}/invocations \
    --region ${AWS_REGION}

# Add permission for API Gateway to invoke Lambda
aws lambda add-permission \
    --function-name ${FUNCTION_NAME} \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" \
    --region ${AWS_REGION}

# Deploy API
aws apigateway create-deployment \
    --rest-api-id ${API_ID} \
    --stage-name prod \
    --region ${AWS_REGION}

echo "🧪 Testing the deployment..."
# Test the function
echo '{"test": "health"}' | base64 | aws lambda invoke \
    --function-name ${FUNCTION_NAME} \
    --payload fileb:///dev/stdin \
    --region ${AWS_REGION} \
    response.json

echo "📋 Response:"
cat response.json

echo "🌐 API Gateway URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
echo "📋 Test with: curl https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod/health"

echo "✅ Container-based deployment completed successfully!"
echo "📋 Function ARN: arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}"
echo "📋 ECR Image: ${ECR_URI}:${IMAGE_TAG}"
echo "📋 API Gateway URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
