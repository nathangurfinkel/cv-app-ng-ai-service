# CV Builder AI Service

AI-powered CV generation, evaluation, and utility services designed to run on AWS Lambda.

## Overview

This service handles all AI-related operations for the CV Builder application:
- CV tailoring and generation
- CV evaluation and analysis
- Template recommendations

## Architecture

- **Platform**: AWS Lambda
- **Framework**: FastAPI with Mangum adapter
- **AI Provider**: OpenAI
- **Vector Database**: ChromaDB/Pinecone
- **Evaluation**: RAGAS framework

## Environment Setup

### 1. Create Environment File

```bash
cp env.example .env
```

### 2. Configure Required Variables

Edit `.env` with your actual values:

```env
# REQUIRED
OPENAI_API_KEY=your_openai_api_key_here

# OPTIONAL (for vector storage)
PINECONE_API_KEY=your_pinecone_api_key_here
MOCK_PINECONE=true  # Set to false if using real Pinecone

# CORS (set to your frontend domain)
CORS_ORIGINS=http://localhost:5173

# Debug
DEBUG=false
VERBOSE=false
```

> **Where to get API keys:**
> - **OpenAI**: https://platform.openai.com/api-keys
> - **Pinecone**: https://www.pinecone.io/ (optional)

### 3. Never Commit Secrets

⚠️ **Important**: Never commit `.env` to git. It contains sensitive API keys.

## Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up environment** (see above)

3. **Run locally**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Test the API**:
```bash
curl http://localhost:8000/health
```

## API Endpoints

- `GET /` - Health check
- `GET /health` - Health check
- `POST /ai/cv/tailor` - Tailor CV from text
- `POST /ai/cv/tailor-from-file` - Tailor CV from uploaded file
- `POST /ai/cv/extract-cv-data` - Extract structured CV data
- `POST /ai/cv/rephrase-section` - Rephrase CV section
- `POST /ai/cv/recommend-template` - Recommend CV template
- `POST /ai/evaluation/cv` - Evaluate CV

## Deployment to AWS Lambda

### Automated Deployment (Recommended)

Use the provided deployment script (container image):

```bash
# Deploy with container image (recommended for large dependency trees)
./deploy-container.sh
```

This script will:
- Automatically detect your AWS account ID
- Build and push a Linux/amd64 image to ECR
- Create/update the Lambda function as **packageType=Image**
- Ensure API Gateway can invoke the Lambda (existing API ID)

### Manual Deployment

1. **Set environment variables**:
```bash
export OPENAI_API_KEY="your-key"
export PINECONE_API_KEY="your-key"  # optional
```

2. **Build and push image**:
```bash
docker buildx build --platform linux/amd64 --load -t cv-builder-ai-service:latest .
docker tag cv-builder-ai-service:latest <account-id>.dkr.ecr.eu-north-1.amazonaws.com/cv-builder-ai-service:latest
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-north-1.amazonaws.com/cv-builder-ai-service
docker push <account-id>.dkr.ecr.eu-north-1.amazonaws.com/cv-builder-ai-service:latest
```

3. **Deploy to Lambda (create/update function)**:
```bash
aws lambda update-function-code \
  --function-name cv-builder-ai-service \
  --image-uri <account-id>.dkr.ecr.eu-north-1.amazonaws.com/cv-builder-ai-service:latest \
  --region eu-north-1
```

4. **Set Lambda environment variables**:
```bash
aws lambda update-function-configuration \
  --function-name cv-builder-ai-service \
  --environment Variables='{
    "OPENAI_API_KEY":"your-key",
    "PINECONE_API_KEY":"your-key",
    "MOCK_PINECONE":"false",
    "CORS_ORIGINS":"https://your-frontend.com"
  }' \
  --region eu-north-1
```

## Infrastructure

### AWS Resources

#### Account Information
- **Account ID**: Retrieved via AWS CLI (`aws sts get-caller-identity`)
- **Region**: `eu-north-1` (Stockholm)

#### Lambda Function
- **Function Name**: cv-builder-ai-service
- **Runtime**: Python 3.13
- **Handler**: `app.main.handler`
- **Memory**: 1024 MB
- **Timeout**: 30 seconds
- **Package Type**: Zip or Container Image

#### API Gateway
- **Type**: HTTP API (AWS_PROXY integration)
- **Stage**: prod
- **Base Path**: `/ai`
- **Authentication**: API Key required

### Environment Variables

#### Required for Lambda
Set these in AWS Lambda console or deployment scripts:

```bash
# AI Services
OPENAI_API_KEY=<your-openai-api-key>
PINECONE_API_KEY=<your-pinecone-api-key>
MOCK_PINECONE=false

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com

# Debug Configuration
DEBUG=false
VERBOSE=false
```

### Secrets Management

#### AWS Secrets Manager (Recommended)
Store sensitive keys in AWS Secrets Manager:

```bash
# Store OpenAI key
aws secretsmanager create-secret \
  --name cv-builder/openai-key \
  --secret-string "your-openai-api-key" \
  --region eu-north-1

# Store Pinecone key
aws secretsmanager create-secret \
  --name cv-builder/pinecone-key \
  --secret-string "your-pinecone-api-key" \
  --region eu-north-1
```

#### Never Commit
- ❌ API Keys (OpenAI, Pinecone)
- ❌ AWS Account IDs in code
- ❌ Lambda ARNs with account IDs

#### Safe to Commit
- ✅ Service names
- ✅ Configuration structure
- ✅ Environment variable names (not values)

### IAM Roles

#### Lambda Execution Role
Required policies:
- `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
- Custom policy for Secrets Manager access (if using)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:eu-north-1:*:secret:cv-builder/*"
    }
  ]
}
```

### API Gateway Configuration

#### Rate Limiting
- **Burst Limit**: 100 requests/second
- **Rate Limit**: 50 requests/second
- **Daily Quota**: 10,000 requests

#### API Key Management

```bash
# Create API key
aws apigateway create-api-key \
  --name cv-builder-ai-key \
  --enabled

# Attach to usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --key-type API_KEY
```

### Dependencies

#### Core Libraries
- FastAPI - Web framework
- Mangum - AWS Lambda adapter for ASGI
- OpenAI - AI model access
- LangChain - AI orchestration
- ChromaDB/Pinecone - Vector storage
- RAGAS - Evaluation framework

#### Layer Strategy
- Base dependencies in Lambda layer
- Application code in function package
- Reduces deployment package size

## Custom Domain Setup

### Prerequisites
1. A domain name registered with a DNS provider (e.g., Route 53, Cloudflare, GoDaddy)
2. An SSL certificate in AWS Certificate Manager (ACM) for your domain
3. AWS CLI configured with appropriate permissions

### Step 1: Request SSL Certificate

#### Using AWS Certificate Manager (Recommended)
```bash
# Request a certificate for your domain
aws acm request-certificate \
    --domain-name "api.yourdomain.com" \
    --validation-method DNS \
    --region us-east-1  # Must be us-east-1 for API Gateway custom domains
```

### Step 2: Validate Certificate
1. Go to AWS Certificate Manager console
2. Find your certificate and click "Create record in Route 53" or manually add DNS records
3. Wait for validation (usually 5-10 minutes)

### Step 3: Configure DNS
After setting up custom domain, create a CNAME record:

```
Type: CNAME
Name: api.yourdomain.com
Value: [TARGET_DOMAIN_FROM_AWS]
TTL: 300
```

### Step 4: Update Frontend Configuration
Update your frontend environment variables:

```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_API_KEY=your-api-key
```

### Step 5: Test Custom Domain
```bash
curl -X POST https://api.yourdomain.com/ai/cv/tailor \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{"job_description": "test", "user_cv_text": "test"}'
```

## Monitoring

### CloudWatch Logs
- Log Group: `/aws/lambda/cv-builder-ai-service`
- Retention: 7 days (configurable)

### CloudWatch Metrics
- Invocations
- Duration
- Errors
- Throttles

### Custom Metrics
- CV processing time
- AI model response time
- Evaluation scores

## Troubleshooting

### Cold Start Issues
- Increase memory allocation
- Use provisioned concurrency (paid)
- Optimize imports

### Timeout Issues
- Increase timeout (max 15 minutes)
- Optimize AI model calls
- Use async processing for long tasks

### Dependency Issues
- Check Lambda layer compatibility
- Verify Python version matches runtime
- Test locally with same Python version

### Certificate Issues (Custom Domain)
- Ensure certificate is in `us-east-1` region
- Verify certificate is validated and active
- Check domain name matches exactly

### DNS Issues (Custom Domain)
- Verify CNAME record is correct
- Wait for DNS propagation (5-10 minutes)
- Use `dig` or `nslookup` to verify DNS resolution

## Security Best Practices

### API Keys
- Rotate API keys regularly
- Store in AWS Secrets Manager
- Never log sensitive data

### CORS
- Restrict origins to frontend domain only
- Avoid wildcard (*) origins in production

### Input Validation
- Validate all user inputs
- Sanitize file uploads
- Limit request sizes

### HTTPS Only
- Always use HTTPS for API calls
- Enable CloudWatch logs for monitoring

## Performance Optimization

### Lambda Configuration
- Memory: 1024 MB (balance cost vs. performance)
- Timeout: 30s (adjust based on AI model response times)
- Use ARM64 architecture for cost savings

### AI Model Optimization
- Cache embeddings when possible
- Batch API calls
- Use streaming for long responses

## Cost Management

### Lambda Pricing
- Pay per invocation + duration
- Free tier: 1M requests/month

### API Gateway Pricing
- Pay per request
- Free tier: 1M requests/month

### OpenAI Costs
- Monitor token usage
- Set usage limits
- Cache responses where appropriate

## Additional Resources

- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Mangum Documentation](https://mangum.io/)
