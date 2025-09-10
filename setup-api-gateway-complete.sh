#!/bin/bash

# Complete API Gateway Setup for CV Builder AI Service
# This script sets up API Gateway with proper routing to Lambda function

set -e

# Configuration
REGION="eu-north-1"
FUNCTION_NAME="cv-builder-ai-service"
API_NAME="cv-builder-ai-api"
STAGE_NAME="prod"

echo "🚀 Setting up API Gateway for CV Builder AI Service..."

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"

# Get Lambda function ARN
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
echo "📋 Lambda ARN: $LAMBDA_ARN"

# Create API Gateway
echo "🔧 Creating API Gateway..."
API_ID=$(aws apigateway create-rest-api \
    --name "$API_NAME" \
    --description "CV Builder AI Service API Gateway" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ API Gateway created with ID: $API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[0].id' \
    --output text)

echo "📋 Root Resource ID: $ROOT_RESOURCE_ID"

# Create /ai resource
echo "🔧 Creating /ai resource..."
AI_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_RESOURCE_ID" \
    --path-part "ai" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ /ai resource created with ID: $AI_RESOURCE_ID"

# Create /ai/cv resource
echo "🔧 Creating /ai/cv resource..."
CV_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$AI_RESOURCE_ID" \
    --path-part "cv" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ /ai/cv resource created with ID: $CV_RESOURCE_ID"

# Create /ai/cv/tailor resource
echo "🔧 Creating /ai/cv/tailor resource..."
TAILOR_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$CV_RESOURCE_ID" \
    --path-part "tailor" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ /ai/cv/tailor resource created with ID: $TAILOR_RESOURCE_ID"

# Create /ai/cv/extract-cv-data resource
echo "🔧 Creating /ai/cv/extract-cv-data resource..."
EXTRACT_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$CV_RESOURCE_ID" \
    --path-part "extract-cv-data" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ /ai/cv/extract-cv-data resource created with ID: $EXTRACT_RESOURCE_ID"

# Create /ai/evaluation resource
echo "🔧 Creating /ai/evaluation resource..."
EVAL_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$AI_RESOURCE_ID" \
    --path-part "evaluation" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ /ai/evaluation resource created with ID: $EVAL_RESOURCE_ID"

# Create /ai/evaluation/cv resource
echo "🔧 Creating /ai/evaluation/cv resource..."
EVAL_CV_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$EVAL_RESOURCE_ID" \
    --path-part "cv" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ /ai/evaluation/cv resource created with ID: $EVAL_CV_RESOURCE_ID"

# Add Lambda permission for API Gateway
echo "🔧 Adding Lambda permission for API Gateway..."
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "api-gateway-invoke" \
    --action "lambda:InvokeFunction" \
    --principal "apigateway.amazonaws.com" \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*" \
    --region "$REGION" \
    --output text >/dev/null 2>&1 || echo "⚠️  Permission may already exist"

echo "✅ Lambda permission added"

# Create methods for each endpoint
create_method() {
    local resource_id=$1
    local method=$2
    local path=$3
    
    echo "🔧 Creating $method method for $path..."
    
    # Create method
    aws apigateway put-method \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --authorization-type "NONE" \
        --region "$REGION" \
        --output text >/dev/null 2>&1
    
    # Create method response
    aws apigateway put-method-response \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --status-code "200" \
        --response-parameters method.response.header.Access-Control-Allow-Origin=false,method.response.header.Access-Control-Allow-Headers=false,method.response.header.Access-Control-Allow-Methods=false \
        --region "$REGION" \
        --output text >/dev/null 2>&1
    
    # Create integration
    aws apigateway put-integration \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --type "AWS_PROXY" \
        --integration-http-method "POST" \
        --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations" \
        --region "$REGION" \
        --output text >/dev/null 2>&1
    
    # Create integration response
    aws apigateway put-integration-response \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --status-code "200" \
        --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'","method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'GET,POST,PUT,DELETE,OPTIONS'"'"'"}'
    
    echo "✅ $method method created for $path"
}

# Create methods for all endpoints
create_method "$TAILOR_RESOURCE_ID" "POST" "/ai/cv/tailor"
create_method "$EXTRACT_RESOURCE_ID" "POST" "/ai/cv/extract-cv-data"
create_method "$EVAL_CV_RESOURCE_ID" "POST" "/ai/evaluation/cv"

# Create OPTIONS methods for CORS
create_options_method() {
    local resource_id=$1
    local path=$2
    
    echo "🔧 Creating OPTIONS method for $path..."
    
    # Create OPTIONS method
    aws apigateway put-method \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "OPTIONS" \
        --authorization-type "NONE" \
        --region "$REGION" \
        --output text >/dev/null 2>&1
    
    # Create OPTIONS method response
    aws apigateway put-method-response \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "OPTIONS" \
        --status-code "200" \
        --response-parameters method.response.header.Access-Control-Allow-Origin=false,method.response.header.Access-Control-Allow-Headers=false,method.response.header.Access-Control-Allow-Methods=false \
        --region "$REGION" \
        --output text >/dev/null 2>&1
    
    # Create OPTIONS integration
    aws apigateway put-integration \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "OPTIONS" \
        --type "MOCK" \
        --request-templates '{"application/json":"{\"statusCode\": 200}"}' \
        --region "$REGION" \
        --output text >/dev/null 2>&1
    
    # Create OPTIONS integration response
    aws apigateway put-integration-response \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "OPTIONS" \
        --status-code "200" \
        --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'","method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'GET,POST,PUT,DELETE,OPTIONS'"'"'"}'
    
    echo "✅ OPTIONS method created for $path"
}

# Create OPTIONS methods for CORS
create_options_method "$TAILOR_RESOURCE_ID" "/ai/cv/tailor"
create_options_method "$EXTRACT_RESOURCE_ID" "/ai/cv/extract-cv-data"
create_options_method "$EVAL_CV_RESOURCE_ID" "/ai/evaluation/cv"

# Deploy API
echo "🚀 Deploying API Gateway..."
aws apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name "$STAGE_NAME" \
    --region "$REGION" \
    --output text >/dev/null 2>&1

echo "✅ API Gateway deployed to stage: $STAGE_NAME"

# Get API Gateway URL
API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE_NAME}"

echo ""
echo "🎉 API Gateway Setup Complete!"
echo "=================================="
echo "API Gateway ID: $API_ID"
echo "API URL: $API_URL"
echo ""
echo "Available Endpoints:"
echo "• POST $API_URL/ai/cv/tailor"
echo "• POST $API_URL/ai/cv/extract-cv-data"
echo "• POST $API_URL/ai/evaluation/cv"
echo ""
echo "Test with curl:"
echo "curl -X POST $API_URL/ai/cv/tailor \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"job_description\": \"Software Engineer with Python experience\", \"user_cv_text\": \"John Doe - Software Engineer with 5 years Python experience\"}'"
echo ""
echo "🔧 Next steps:"
echo "1. Test the endpoints with the curl command above"
echo "2. Update your frontend to use the new API URL"
echo "3. Configure custom domain if needed"
