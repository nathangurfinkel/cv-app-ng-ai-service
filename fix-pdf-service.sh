#!/bin/bash

# Fix PDF Service Deployment
# This script creates the missing IAM role and redeploys the PDF service

set -e

REGION="eu-north-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🔧 Fixing PDF Service Deployment..."

# Create ECS Task Role
echo "🔧 Creating ECS Task Role..."
aws iam create-role \
    --role-name ecsTaskRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' \
    --region "$REGION" \
    --output text >/dev/null 2>&1 || echo "⚠️  Role may already exist"

echo "✅ ECS Task Role created"

# Attach necessary policies to the role
echo "🔧 Attaching policies to ECS Task Role..."
aws iam attach-role-policy \
    --role-name ecsTaskRole \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" \
    --region "$REGION" \
    --output text >/dev/null 2>&1 || echo "⚠️  Policy may already be attached"

# Attach additional policies for ECR access
aws iam attach-role-policy \
    --role-name ecsTaskRole \
    --policy-arn "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" \
    --region "$REGION" \
    --output text >/dev/null 2>&1 || echo "⚠️  Policy may already be attached"

echo "✅ Policies attached to ECS Task Role"

# Get the task definition ARN
TASK_DEF_ARN=$(aws ecs describe-task-definition \
    --task-definition cv-pdf-service \
    --region "$REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "📋 Current Task Definition: $TASK_DEF_ARN"

# Update the service to use the correct role
echo "🔧 Updating ECS service..."
aws ecs update-service \
    --cluster cv-builder-cluster \
    --service cv-pdf-service \
    --task-definition cv-pdf-service \
    --region "$REGION" \
    --output text >/dev/null 2>&1

echo "✅ ECS service updated"

# Wait for service to stabilize
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster cv-builder-cluster \
    --services cv-pdf-service \
    --region "$REGION" || echo "⚠️  Service may still be starting"

# Check service status
echo "📊 Checking service status..."
aws ecs describe-services \
    --cluster cv-builder-cluster \
    --services cv-pdf-service \
    --region "$REGION" \
    --query 'services[0].{Name:serviceName,Status:status,RunningCount:runningCount,DesiredCount:desiredCount}' \
    --output table

# Get task ARNs
TASK_ARNS=$(aws ecs list-tasks \
    --cluster cv-builder-cluster \
    --service-name cv-pdf-service \
    --region "$REGION" \
    --query 'taskArns' \
    --output text)

if [ ! -z "$TASK_ARNS" ]; then
    echo "📋 Running Tasks:"
    for task_arn in $TASK_ARNS; do
        echo "  - $task_arn"
    done
    
    # Get task details
    echo "📊 Task Details:"
    aws ecs describe-tasks \
        --cluster cv-builder-cluster \
        --tasks $TASK_ARNS \
        --region "$REGION" \
        --query 'tasks[0].{TaskArn:taskArn,LastStatus:lastStatus,DesiredStatus:desiredStatus,HealthStatus:healthStatus}' \
        --output table
else
    echo "⚠️  No tasks running yet"
fi

echo ""
echo "🎉 PDF Service Fix Complete!"
echo "=================================="
echo "If the service is still not running, check:"
echo "1. CloudWatch logs for error details"
echo "2. ECS service events for more information"
echo "3. Task definition configuration"
echo ""
echo "To check logs:"
echo "aws logs describe-log-groups --log-group-name-prefix '/ecs/cv-pdf-service' --region $REGION"
