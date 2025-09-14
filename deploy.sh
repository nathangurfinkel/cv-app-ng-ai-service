#!/bin/bash

# AI Service Deployment Script for AWS Lambda
# This script packages and deploys the AI service to AWS Lambda

set -e

echo "🚀 Starting AI Service deployment to AWS Lambda..."

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
REGION="eu-north-1"  # Stockholm region
RUNTIME="python3.11"
HANDLER="app.main.handler"
MEMORY_SIZE="512"
TIMEOUT="30"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create deployment package
echo "📦 Creating deployment package..."
rm -rf package/
mkdir -p package

# Install optimized dependencies for cloud deployment using Docker for Linux compatibility
echo "📥 Installing optimized dependencies for Linux Lambda runtime..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.11 sh -c "pip install --no-cache-dir setuptools wheel && pip install --no-cache-dir -r requirements.txt -t package/"

# Copy only essential application code AFTER installing dependencies
echo "📋 Copying application code..."
mkdir -p package/app
cp -r app/* package/app/

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
find package/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find package/ -type f -name "*.pyc" -delete 2>/dev/null || true
find package/ -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find package/ -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find package/ -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find package/ -type f -name "*.md" -delete 2>/dev/null || true
find package/ -type f -name "*.txt" -not -name "requirements.txt" -delete 2>/dev/null || true

# Create deployment zip with only essential files
echo "🗜️ Creating deployment package..."
cd package
zip -r ../ai-service-deployment.zip . -x "*.pyc" "__pycache__/*" "*.git*" "*.DS_Store*" "*.dist-info/*" "*/__pycache__/*"
cd ..

echo "✅ Deployment package created: ai-service-deployment.zip"

# Deploy to AWS Lambda (requires AWS CLI to be configured)
if command -v aws &> /dev/null; then
    echo "☁️ Deploying to AWS Lambda..."
    
    # Check if function exists
    if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
        echo "🔄 Updating existing Lambda function..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://ai-service-deployment.zip \
            --region $REGION
    else
        echo "🆕 Creating new Lambda function..."
        aws lambda create-function \
            --function-name $FUNCTION_NAME \
            --runtime $RUNTIME \
            --role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
            --handler $HANDLER \
            --zip-file fileb://ai-service-deployment.zip \
            --memory-size $MEMORY_SIZE \
            --timeout $TIMEOUT \
            --region $REGION
    fi
    
    echo "✅ AI Service deployed successfully!"
    echo "🔗 Function ARN: arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
else
    echo "⚠️ AWS CLI not found. Please install and configure AWS CLI to deploy."
    echo "📦 Deployment package ready: ai-service-deployment.zip"
fi

echo "🎉 Deployment process completed!"
