#!/bin/bash

# Complete deployment script for Python 3.13 RAG stack
set -e

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
REGION="eu-north-1"
ACCOUNT_ID="303774815769"
HANDLER="app.main.handler"
RUNTIME="python3.13"
MEMORY_SIZE="1024"
TIMEOUT="30"

echo "🚀 Starting complete deployment for Python 3.13 RAG stack..."

# Create deployment package
echo "📦 Creating deployment package..."
rm -rf deployment-package
mkdir -p deployment-package

# Copy application code
cp -r app deployment-package/
cp requirements.txt deployment-package/

# Install dependencies
echo "📚 Installing dependencies..."
cd deployment-package
pip install -r requirements.txt -t .
cd ..

# Create ZIP package
echo "🗜️ Creating ZIP package..."
cd deployment-package
zip -r ../ai-service-deployment-313.zip .
cd ..

# Delete existing function if it exists
echo "🗑️ Deleting existing Lambda function..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION"
    echo "⏳ Waiting for function deletion..."
    sleep 10
fi

# Create Lambda function
echo "🚀 Creating Lambda function..."
aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --role "arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role" \
    --handler "$HANDLER" \
    --zip-file fileb://ai-service-deployment-313.zip \
    --memory-size "$MEMORY_SIZE" \
    --timeout "$TIMEOUT" \
    --region "$REGION"

# Wait for function to be active
echo "⏳ Waiting for function to be active..."
aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$REGION"

# Set environment variables
echo "🔧 Setting environment variables..."
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --environment Variables='{
        "MOCK_PINECONE": "false",
        "PINECONE_API_KEY": "'${PINECONE_API_KEY}'",
        "OPENAI_API_KEY": "'${OPENAI_API_KEY}'",
        "VERBOSE": "false",
        "CORS_ORIGINS": "'${CORS_ORIGINS:-https://main.d3q8q8q8q8q8q8.amplifyapp.com}'",
        "DEBUG": "false"
    }' \
    --region "$REGION"

# Create API Gateway
echo "🌐 Creating API Gateway..."
if aws apigateway get-rest-api --rest-api-id "$(aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text --region "$REGION")" --region "$REGION" >/dev/null 2>&1; then
    echo "API Gateway already exists, skipping creation..."
    API_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text --region "$REGION")
else
    API_ID=$(aws apigateway create-rest-api \
        --name "$FUNCTION_NAME-api" \
        --description "API Gateway for $FUNCTION_NAME" \
        --region "$REGION" \
        --query 'id' \
        --output text)
    echo "📋 API Gateway ID: $API_ID"
fi

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[0].id' \
    --output text)

# Create proxy resource
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_RESOURCE_ID" \
    --path-part '{proxy+}' \
    --region "$REGION" \
    --query 'id' \
    --output text)

# Create ANY method
aws apigateway put-method \
    --rest-api-id "$API_ID" \
    --resource-id "$PROXY_RESOURCE_ID" \
    --http-method ANY \
    --authorization-type NONE \
    --region "$REGION"

# Create integration
aws apigateway put-integration \
    --rest-api-id "$API_ID" \
    --resource-id "$PROXY_RESOURCE_ID" \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME/invocations" \
    --region "$REGION"

# Add permission for API Gateway to invoke Lambda
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*" \
    --region "$REGION"

# Deploy API
aws apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name prod \
    --region "$REGION"

echo "🧪 Testing the deployment..."
# Test the function
echo '{"test": "health"}' | base64 | aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload fileb:///dev/stdin \
    --region "$REGION" \
    response.json

echo "📋 Response:"
cat response.json

echo "🌐 API Gateway URL: https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
echo "📋 Test with: curl https://$API_ID.execute-api.$REGION.amazonaws.com/prod/health"

echo "✅ Complete deployment finished successfully!"
echo "📋 Function ARN: arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
echo "📋 API Gateway URL: https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
