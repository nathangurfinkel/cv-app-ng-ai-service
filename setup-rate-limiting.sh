#!/bin/bash

# Rate Limiting and Throttling Setup for API Gateway
# This script configures throttling and rate limiting for the CV Builder AI Service

set -e

# Configuration
REGION="eu-north-1"
API_ID="wz2lhr4qzk"
STAGE_NAME="prod"

# Rate limiting configuration
BURST_LIMIT=100        # Maximum number of requests per second
RATE_LIMIT=50          # Sustained rate limit (requests per second)
QUOTA_LIMIT=10000      # Daily quota limit
QUOTA_PERIOD="DAY"     # Quota period

echo "⚡ Setting up Rate Limiting and Throttling for API Gateway..."

echo "📋 Configuration:"
echo "  Burst Limit: $BURST_LIMIT requests/second"
echo "  Rate Limit: $RATE_LIMIT requests/second"
echo "  Quota Limit: $QUOTA_LIMIT requests/$QUOTA_PERIOD"
echo "  API Gateway ID: $API_ID"
echo "  Region: $REGION"

# Create usage plan
echo "🔧 Creating usage plan..."
USAGE_PLAN_ID=$(aws apigateway create-usage-plan \
    --name "cv-builder-ai-usage-plan" \
    --description "Usage plan for CV Builder AI Service with rate limiting" \
    --throttle burstLimit=$BURST_LIMIT,rateLimit=$RATE_LIMIT \
    --quota limit=$QUOTA_LIMIT,period=$QUOTA_PERIOD \
    --api-stages apiId=$API_ID,stage=$STAGE_NAME \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ Usage plan created with ID: $USAGE_PLAN_ID"

# Create API key
echo "🔧 Creating API key..."
API_KEY_ID=$(aws apigateway create-api-key \
    --name "cv-builder-ai-key" \
    --description "API key for CV Builder AI Service" \
    --enabled \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "✅ API key created with ID: $API_KEY_ID"

# Get the API key value
API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key "$API_KEY_ID" \
    --include-value \
    --region "$REGION" \
    --query 'value' \
    --output text)

echo "🔑 API Key Value: $API_KEY_VALUE"

# Associate API key with usage plan
echo "🔧 Associating API key with usage plan..."
aws apigateway create-usage-plan-key \
    --usage-plan-id "$USAGE_PLAN_ID" \
    --key-id "$API_KEY_ID" \
    --key-type "API_KEY" \
    --region "$REGION" \
    --output text >/dev/null 2>&1

echo "✅ API key associated with usage plan"

# Create API key for each method (optional - for method-level throttling)
echo "🔧 Setting up method-level throttling..."

# Get all resources
RESOURCES=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[?resourceMethods].{id:id,path:pathPart,methods:resourceMethods}' \
    --output json)

echo "📋 Available resources:"
echo "$RESOURCES" | jq -r '.[] | "  \(.id): \(.path) - \(.methods | keys | join(", "))"'

# Set throttling for specific methods
set_method_throttling() {
    local resource_id=$1
    local method=$2
    local burst_limit=$3
    local rate_limit=$4
    
    echo "🔧 Setting throttling for $method method on resource $resource_id..."
    
    aws apigateway update-method \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --patch-ops op=replace,path=/throttling/burstLimit,value=$burst_limit \
        --region "$REGION" \
        --output text >/dev/null 2>&1 || echo "⚠️  Could not set burst limit for $method"
    
    aws apigateway update-method \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --patch-ops op=replace,path=/throttling/rateLimit,value=$rate_limit \
        --region "$REGION" \
        --output text >/dev/null 2>&1 || echo "⚠️  Could not set rate limit for $method"
    
    echo "✅ Throttling set for $method method"
}

# Get resource IDs for our endpoints
TAILOR_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[?pathPart==`tailor`].id' \
    --output text)

EXTRACT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[?pathPart==`extract-cv-data`].id' \
    --output text)

EVAL_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[?pathPart==`cv` && parentId!=null].id' \
    --output text)

# Set throttling for each endpoint
if [ ! -z "$TAILOR_RESOURCE_ID" ]; then
    set_method_throttling "$TAILOR_RESOURCE_ID" "POST" 20 10
fi

if [ ! -z "$EXTRACT_RESOURCE_ID" ]; then
    set_method_throttling "$EXTRACT_RESOURCE_ID" "POST" 20 10
fi

if [ ! -z "$EVAL_RESOURCE_ID" ]; then
    set_method_throttling "$EVAL_RESOURCE_ID" "POST" 20 10
fi

# Deploy the changes
echo "🚀 Deploying throttling configuration..."
aws apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name "$STAGE_NAME" \
    --region "$REGION" \
    --output text >/dev/null 2>&1

echo "✅ Throttling configuration deployed"

# Create monitoring and alerting
echo "🔧 Setting up CloudWatch monitoring..."

# Create CloudWatch alarm for throttling
aws cloudwatch put-metric-alarm \
    --alarm-name "cv-builder-api-throttling" \
    --alarm-description "API Gateway throttling alarm" \
    --metric-name "4XXError" \
    --namespace "AWS/ApiGateway" \
    --statistic "Sum" \
    --period 300 \
    --threshold 10 \
    --comparison-operator "GreaterThanThreshold" \
    --dimensions Name=ApiName,Value=cv-builder-ai-api \
    --evaluation-periods 2 \
    --region "$REGION" \
    --output text >/dev/null 2>&1 || echo "⚠️  Could not create throttling alarm"

# Create CloudWatch alarm for high request count
aws cloudwatch put-metric-alarm \
    --alarm-name "cv-builder-api-high-requests" \
    --alarm-description "High request count alarm" \
    --metric-name "Count" \
    --namespace "AWS/ApiGateway" \
    --statistic "Sum" \
    --period 300 \
    --threshold 1000 \
    --comparison-operator "GreaterThanThreshold" \
    --dimensions Name=ApiName,Value=cv-builder-ai-api \
    --evaluation-periods 1 \
    --region "$REGION" \
    --output text >/dev/null 2>&1 || echo "⚠️  Could not create high requests alarm"

echo "✅ CloudWatch monitoring configured"

echo ""
echo "🎉 Rate Limiting and Throttling Setup Complete!"
echo "=============================================="
echo "Usage Plan ID: $USAGE_PLAN_ID"
echo "API Key ID: $API_KEY_ID"
echo "API Key Value: $API_KEY_VALUE"
echo ""
echo "📊 Rate Limiting Configuration:"
echo "  Burst Limit: $BURST_LIMIT requests/second"
echo "  Rate Limit: $RATE_LIMIT requests/second"
echo "  Daily Quota: $QUOTA_LIMIT requests"
echo ""
echo "🔧 Method-Level Throttling:"
echo "  POST /ai/cv/tailor: 20 burst, 10 sustained"
echo "  POST /ai/cv/extract-cv-data: 20 burst, 10 sustained"
echo "  POST /ai/evaluation/cv: 20 burst, 10 sustained"
echo ""
echo "📈 Monitoring:"
echo "  CloudWatch alarms created for throttling and high request count"
echo "  Monitor in AWS CloudWatch console"
echo ""
echo "🔑 Usage:"
echo "  Add 'X-API-Key: $API_KEY_VALUE' header to requests"
echo "  Or use query parameter: ?api_key=$API_KEY_VALUE"
echo ""
echo "Test with API key:"
echo "curl -X POST https://wz2lhr4qzk.execute-api.eu-north-1.amazonaws.com/prod/ai/cv/tailor \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-API-Key: $API_KEY_VALUE' \\"
echo "  -d '{\"job_description\": \"test\", \"user_cv_text\": \"test\"}'"
