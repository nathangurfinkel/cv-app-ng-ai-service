#!/bin/bash

# Custom Domain Setup for API Gateway
# This script sets up a custom domain for the CV Builder AI Service API Gateway

set -e

# Configuration
REGION="eu-north-1"
API_ID="wz2lhr4qzk"
STAGE_NAME="prod"
DOMAIN_NAME="cv-builder-api"  # Change this to your desired domain
CERTIFICATE_ARN=""  # You'll need to provide this

echo "🌐 Setting up Custom Domain for API Gateway..."

# Check if domain name is provided
if [ -z "$DOMAIN_NAME" ]; then
    echo "❌ Please set DOMAIN_NAME variable in the script"
    exit 1
fi

# Check if certificate ARN is provided
if [ -z "$CERTIFICATE_ARN" ]; then
    echo "🔍 Searching for SSL certificate in ACM..."
    
    # List certificates in the region
    CERTIFICATES=$(aws acm list-certificates --region "$REGION" --query 'CertificateSummaryList[].{Arn:CertificateArn,DomainName:DomainName}' --output table)
    echo "Available certificates:"
    echo "$CERTIFICATES"
    
    echo ""
    echo "⚠️  Please provide a valid certificate ARN for your domain"
    echo "You can get one from AWS Certificate Manager (ACM)"
    echo "Example: arn:aws:acm:eu-north-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
    echo ""
    read -p "Enter Certificate ARN: " CERTIFICATE_ARN
    
    if [ -z "$CERTIFICATE_ARN" ]; then
        echo "❌ Certificate ARN is required for custom domain setup"
        exit 1
    fi
fi

echo "📋 Configuration:"
echo "  Domain Name: $DOMAIN_NAME"
echo "  Certificate ARN: $CERTIFICATE_ARN"
echo "  API Gateway ID: $API_ID"
echo "  Region: $REGION"

# Create custom domain
echo "🔧 Creating custom domain..."
DOMAIN_NAME_ID=$(aws apigateway create-domain-name \
    --domain-name "$DOMAIN_NAME" \
    --certificate-arn "$CERTIFICATE_ARN" \
    --endpoint-configuration types=REGIONAL \
    --region "$REGION" \
    --query 'domainName' \
    --output text)

echo "✅ Custom domain created: $DOMAIN_NAME_ID"

# Get the target domain name for DNS configuration
TARGET_DOMAIN=$(aws apigateway get-domain-name \
    --domain-name "$DOMAIN_NAME" \
    --region "$REGION" \
    --query 'distributionDomainName' \
    --output text)

echo "📋 Target Domain for DNS: $TARGET_DOMAIN"

# Create base path mapping
echo "🔧 Creating base path mapping..."
aws apigateway create-base-path-mapping \
    --domain-name "$DOMAIN_NAME" \
    --base-path "" \
    --rest-api-id "$API_ID" \
    --stage "$STAGE_NAME" \
    --region "$REGION" \
    --output text >/dev/null 2>&1

echo "✅ Base path mapping created"

# Get the API Gateway URL
API_URL="https://${DOMAIN_NAME}"

echo ""
echo "🎉 Custom Domain Setup Complete!"
echo "=================================="
echo "Custom Domain: $API_URL"
echo "Target Domain (for DNS): $TARGET_DOMAIN"
echo ""
echo "🔧 DNS Configuration Required:"
echo "Create a CNAME record in your DNS provider:"
echo "  Name: $DOMAIN_NAME"
echo "  Value: $TARGET_DOMAIN"
echo "  TTL: 300 (5 minutes)"
echo ""
echo "📋 Available Endpoints:"
echo "• POST $API_URL/ai/cv/tailor"
echo "• POST $API_URL/ai/cv/extract-cv-data"
echo "• POST $API_URL/ai/evaluation/cv"
echo ""
echo "⚠️  Note: DNS propagation may take 5-10 minutes"
echo "Test with: curl -X POST $API_URL/ai/cv/tailor -H 'Content-Type: application/json' -d '{\"job_description\": \"test\", \"user_cv_text\": \"test\"}'"
