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

# Create deployment package
echo "📦 Creating deployment package..."
rm -rf package/
mkdir -p package

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t package/

# Copy application code
echo "📋 Copying application code..."
cp -r app/ package/
cp -r templates/ package/ 2>/dev/null || true

# Create deployment zip
echo "🗜️ Creating deployment package..."
cd package
zip -r ../ai-service-deployment.zip .
cd ..

echo "✅ Deployment package created: ai-service-deployment.zip"

# Deploy to AWS Lambda (requires AWS CLI to be configured)
if command -v aws &> /dev/null; then
    echo "☁️ Deploying to AWS Lambda..."
    
    # Check if function exists
    if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
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
            --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
            --handler $HANDLER \
            --zip-file fileb://ai-service-deployment.zip \
            --memory-size $MEMORY_SIZE \
            --timeout $TIMEOUT \
            --region $REGION
    fi
    
    echo "✅ AI Service deployed successfully!"
    echo "🔗 Function ARN: arn:aws:lambda:$REGION:YOUR_ACCOUNT_ID:function:$FUNCTION_NAME"
else
    echo "⚠️ AWS CLI not found. Please install and configure AWS CLI to deploy."
    echo "📦 Deployment package ready: ai-service-deployment.zip"
fi

echo "🎉 Deployment process completed!"
