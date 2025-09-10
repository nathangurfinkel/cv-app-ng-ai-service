#!/bin/bash

# AI Service Docker Deployment Script for AWS Lambda
# This script builds a Docker image and deploys it to AWS Lambda

set -e

echo "🚀 Starting AI Service Docker deployment to AWS Lambda..."

# Configuration
FUNCTION_NAME="cv-builder-ai-service"
REGION="eu-north-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="cv-builder-ai-service"
IMAGE_TAG="latest"
ROLE_NAME="lambda-execution-role"

echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "ECR Repository: $ECR_REPOSITORY"

# Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $REGION >/dev/null 2>&1 || \
aws ecr create-repository \
    --repository-name $ECR_REPOSITORY \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true

# Get ECR login token
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image for x86_64 architecture (Lambda requirement)
echo "🏗️ Building Docker image for x86_64 architecture..."
docker build --platform linux/amd64 -t $ECR_REPOSITORY:$IMAGE_TAG .

# Tag image for ECR
docker tag $ECR_REPOSITORY:$IMAGE_TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Create IAM role if it doesn't exist
echo "👤 Creating IAM role..."
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || echo "Role already exists"

# Attach basic execution policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait for role to be ready
echo "⏳ Waiting for IAM role to be ready..."
sleep 10

# Deploy to Lambda
echo "🚀 Deploying to AWS Lambda..."

# Check if function exists and delete if it's a ZIP package
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "🔍 Checking existing function package type..."
    PACKAGE_TYPE=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.PackageType' --output text)
    
    if [ "$PACKAGE_TYPE" = "Zip" ]; then
        echo "🗑️ Deleting existing ZIP-based function to replace with container..."
        aws lambda delete-function --function-name $FUNCTION_NAME --region $REGION
        echo "⏳ Waiting for function deletion to complete..."
        sleep 10
    else
        echo "🔄 Updating existing container-based function..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG \
            --region $REGION
        exit 0
    fi
fi

echo "🆕 Creating new Lambda function with container image..."
aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --package-type Image \
    --code ImageUri=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG \
    --role arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME \
    --timeout 30 \
    --memory-size 1024 \
    --region $REGION \
    --description "CV Builder AI Service - Containerized"

echo "✅ AI Service deployed successfully!"
echo "🔗 Function ARN: arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
echo "🐳 Image URI: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
