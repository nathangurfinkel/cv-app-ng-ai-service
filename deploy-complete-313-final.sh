#!/bin/bash

# Complete deployment script for Python 3.13 with all fixes
# This script addresses all the issues we've encountered:
# - numpy source directory conflict
# - pydantic binary compatibility
# - layer size limits
# - missing dependencies

set -e

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
REGION="eu-north-1"
RUNTIME="python3.13"
HANDLER="app.main.handler"
ROLE_ARN="arn:aws:iam::303774815769:role/lambda-execution-role"
LAYER_NAME="minimal-dependencies-313-with-numpy"

echo "🚀 Starting complete deployment for Python 3.13..."

# Step 1: Create the layer with numpy
echo "📦 Creating layer with numpy..."
./create-minimal-layer-313-with-numpy.sh

# Get the latest layer ARN
LAYER_ARN=$(aws lambda list-layer-versions --layer-name $LAYER_NAME --region $REGION --query 'LayerVersions[0].LayerVersionArn' --output text)
echo "📋 Using layer: $LAYER_ARN"

# Step 2: Clean up previous deployment
echo "🧹 Cleaning up previous deployment..."
rm -rf package
mkdir -p package

# Step 3: Copy application code
echo "📁 Copying application code..."
cp -r app package/

# Step 4: Install dependencies without pydantic
echo "📥 Installing dependencies (excluding pydantic)..."
pip install --no-cache-dir --target package/ -r requirements-no-pydantic.txt

# Step 5: Remove pydantic from deployment package to avoid conflicts
echo "🗑️ Removing pydantic from deployment package..."
rm -rf package/pydantic* package/annotated_types*

# Step 6: Create deployment package
echo "📦 Creating deployment package..."
cd package
zip -r ../deployment-313-final.zip .
cd ..

# Step 7: Delete and recreate Lambda function to ensure clean state
echo "🗑️ Deleting existing Lambda function..."
aws lambda delete-function --function-name $FUNCTION_NAME --region $REGION || echo "Function doesn't exist, continuing..."

# Step 8: Create new Lambda function
echo "🚀 Creating new Lambda function..."
aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime $RUNTIME \
    --role $ROLE_ARN \
    --handler $HANDLER \
    --zip-file fileb://deployment-313-final.zip \
    --timeout 30 \
    --memory-size 512 \
    --layers $LAYER_ARN \
    --region $REGION

# Step 9: Wait for function to be active
echo "⏳ Waiting for function to be active..."
aws lambda wait function-active --function-name $FUNCTION_NAME --region $REGION

# Step 10: Set environment variables
echo "🔧 Setting environment variables..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment file://env-vars.json \
    --region $REGION

# Step 11: Wait for configuration update
echo "⏳ Waiting for configuration update..."
aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION

# Step 12: Create API Gateway
echo "🌐 Creating API Gateway..."
API_ID=$(aws apigateway create-rest-api \
    --name "cv-builder-ai-api" \
    --description "API Gateway for CV Builder AI Service" \
    --region $REGION \
    --query 'id' \
    --output text)

echo "📋 API Gateway ID: $API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[0].id' \
    --output text)

# Create proxy resource
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method ANY \
    --authorization-type NONE \
    --region $REGION

# Set up Lambda integration
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:303774815769:function:$FUNCTION_NAME/invocations" \
    --region $REGION

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION

# Add permission for API Gateway to invoke Lambda
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:303774815769:$API_ID/*/*" \
    --region $REGION

# Step 13: Test the deployment
echo "🧪 Testing the deployment..."
echo '{"httpMethod": "GET", "path": "/health", "headers": {}, "queryStringParameters": null, "body": null, "isBase64Encoded": false}' | base64 > test-payload.b64

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload file://test-payload.b64 \
    --region $REGION \
    response.json

echo "📋 Response:"
cat response.json

# Step 14: Display API Gateway URL
API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
echo "🌐 API Gateway URL: $API_URL"
echo "📋 Test with: curl $API_URL/health"

echo "✅ Deployment completed successfully!"
echo "📋 Function ARN: arn:aws:lambda:$REGION:303774815769:function:$FUNCTION_NAME"
echo "📋 Layer ARN: $LAYER_ARN"
echo "📋 API Gateway URL: $API_URL"
