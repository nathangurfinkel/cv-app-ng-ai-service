#!/bin/bash

# AI Service Deployment Script with Python 3.13 LangChain Layer
# This script packages and deploys the AI service using a pre-built LangChain layer

set -e

echo "🚀 Starting AI Service deployment with Python 3.13 LangChain layer..."

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
REGION="eu-north-1"
RUNTIME="python3.13"
HANDLER="app.main.handler"
MEMORY_SIZE="512"
TIMEOUT="30"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check if layer ARN exists
if [ -f "layer-arn-313-minimal.txt" ]; then
    LAYER_ARN=$(cat layer-arn-313-minimal.txt)
    echo "📋 Using existing layer: $LAYER_ARN"
else
    echo "❌ Layer ARN not found. Please run create-langchain-layer-313-minimal.sh first."
    exit 1
fi

# Create deployment package
echo "📦 Creating minimal deployment package..."
rm -rf package/
mkdir -p package

# Install minimal dependencies for cloud deployment
echo "📥 Installing minimal dependencies..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.13 sh -c "
pip install --no-cache-dir --target package/ -r requirements-minimal.txt
"

# Copy application code
echo "📋 Copying application code..."
cp -r app/ package/

# Create deployment zip
echo "📦 Creating deployment package..."
cd package
zip -r ../ai-service-deployment-313.zip .
cd ..

# Get package size
PACKAGE_SIZE=$(du -h ai-service-deployment-313.zip | cut -f1)
echo "📊 Package size: $PACKAGE_SIZE"

# Update function code
echo "☁️ Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --zip-file fileb://ai-service-deployment-313.zip

# Update function configuration
echo "⚙️ Updating Lambda function configuration..."
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --runtime "$RUNTIME" \
    --handler "$HANDLER" \
    --memory-size "$MEMORY_SIZE" \
    --timeout "$TIMEOUT" \
    --layers "$LAYER_ARN"

# Wait for function to be ready
echo "⏳ Waiting for function to be ready..."
aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION"

# Get function info
echo "📋 Function information:"
aws lambda get-function \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --query 'Configuration.{FunctionName:FunctionName,State:State,LastModified:LastModified,CodeSize:CodeSize,Runtime:Runtime}' \
    --output table

echo "✅ Deployment completed successfully!"
echo "🎉 AI Service is now running with Python 3.13 and LangChain layer!"
echo "📝 Function: $FUNCTION_NAME"
echo "🌍 Region: $REGION"
echo "🐍 Runtime: $RUNTIME"
echo "📦 Layer: $LAYER_ARN"
