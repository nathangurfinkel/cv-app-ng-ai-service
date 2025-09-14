#!/bin/bash

# AI Service Deployment Script with LangChain Layer
# This script packages and deploys the AI service using a pre-built LangChain layer

set -e

echo "🚀 Starting AI Service deployment with LangChain layer..."

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
REGION="eu-north-1"
RUNTIME="python3.11"
HANDLER="app.main.handler"
MEMORY_SIZE="512"
TIMEOUT="30"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check if layer ARN exists
if [ -f "layer-arn.txt" ]; then
    LAYER_ARN=$(cat layer-arn.txt)
    echo "📋 Using existing layer: $LAYER_ARN"
else
    echo "❌ Layer ARN not found. Please run create-langchain-layer.sh first."
    exit 1
fi

# Create deployment package
echo "📦 Creating minimal deployment package..."
rm -rf package/
mkdir -p package

# Install minimal dependencies for cloud deployment
echo "📥 Installing minimal dependencies..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.11 sh -c "pip install --no-cache-dir setuptools wheel && pip install --no-cache-dir -r requirements-minimal.txt -t package/"

# Copy only essential application code
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
find package/ -type f -name "*.txt" -not -name "requirements*.txt" -delete 2>/dev/null || true

# Create deployment zip with only essential files
echo "🗜️ Creating deployment package..."
cd package
zip -r ../ai-service-deployment-minimal.zip . -x "*.pyc" "__pycache__/*" "*.git*" "*.DS_Store*" "*.dist-info/*" "*/__pycache__/*"
cd ..

echo "✅ Minimal deployment package created: ai-service-deployment-minimal.zip"

# Deploy to AWS Lambda
if command -v aws &> /dev/null; then
    echo "☁️ Deploying to AWS Lambda with layer..."
    
    # Check if function exists
    if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
        echo "🔄 Updating existing Lambda function with layer..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://ai-service-deployment-minimal.zip \
            --region $REGION
        
        # Update function configuration to include the layer
        echo "🔧 Updating function configuration with layer..."
        aws lambda update-function-configuration \
            --function-name $FUNCTION_NAME \
            --layers $LAYER_ARN \
            --region $REGION
    else
        echo "🆕 Creating new Lambda function with layer..."
        aws lambda create-function \
            --function-name $FUNCTION_NAME \
            --runtime $RUNTIME \
            --role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
            --handler $HANDLER \
            --zip-file fileb://ai-service-deployment-minimal.zip \
            --memory-size $MEMORY_SIZE \
            --timeout $TIMEOUT \
            --layers $LAYER_ARN \
            --region $REGION
    fi
    
    echo "✅ AI Service deployed successfully with LangChain layer!"
    echo "🔗 Function ARN: arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
    echo "📦 Layer ARN: $LAYER_ARN"
else
    echo "⚠️ AWS CLI not found. Please install and configure AWS CLI to deploy."
    echo "📦 Deployment package ready: ai-service-deployment-minimal.zip"
fi

echo "🎉 Deployment process completed!"
