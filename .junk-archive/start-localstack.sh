#!/bin/bash
# Quick start script for LocalStack

set -e

echo "=========================================="
echo "Starting LocalStack for CV Builder AI Service"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo ""
    echo "Please start Docker Desktop first, then run this script again."
    echo ""
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Start LocalStack
echo "Starting LocalStack container..."
docker compose -f docker-compose.localstack.yml up -d

echo ""
echo "Waiting for LocalStack to be ready (10 seconds)..."
sleep 10

# Check health
echo "Checking LocalStack health..."
if curl -s http://localhost:4566/_localstack/health > /dev/null; then
    echo "✓ LocalStack is ready!"
else
    echo "⚠️  LocalStack may still be starting. Wait a few more seconds."
fi

echo ""
echo "Setting up DynamoDB table and SQS queue..."
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

./scripts/setup-localstack.sh

echo ""
echo "=========================================="
echo "✅ LocalStack is ready!"
echo "=========================================="
echo ""
echo "Your AI service should now be able to create async jobs."
echo "Make sure your .env file has:"
echo "  AWS_ENDPOINT_URL=http://localhost:4566"
echo "  JOBS_TABLE_NAME=cv-builder-jobs"
echo "  JOBS_QUEUE_URL=http://localhost:4566/000000000000/cv-builder-jobs-queue"
echo ""
