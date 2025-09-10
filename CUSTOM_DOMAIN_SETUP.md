# Custom Domain Setup for CV Builder AI Service

## Overview
This document provides instructions for setting up a custom domain for the CV Builder AI Service API Gateway.

## Prerequisites
1. A domain name registered with a DNS provider (e.g., Route 53, Cloudflare, GoDaddy)
2. An SSL certificate in AWS Certificate Manager (ACM) for your domain
3. AWS CLI configured with appropriate permissions

## Step 1: Request SSL Certificate

### Option A: Using AWS Certificate Manager (Recommended)
```bash
# Request a certificate for your domain
aws acm request-certificate \
    --domain-name "api.yourdomain.com" \
    --validation-method DNS \
    --region us-east-1  # Must be us-east-1 for API Gateway custom domains
```

### Option B: Using Existing Certificate
If you already have a certificate, note its ARN from the ACM console.

## Step 2: Validate Certificate
1. Go to AWS Certificate Manager console
2. Find your certificate and click "Create record in Route 53" or manually add DNS records
3. Wait for validation (usually 5-10 minutes)

## Step 3: Set Up Custom Domain

### Update the setup script with your domain:
```bash
# Edit setup-custom-domain.sh
DOMAIN_NAME="api.yourdomain.com"  # Your custom domain
CERTIFICATE_ARN="arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
```

### Run the setup script:
```bash
./setup-custom-domain.sh
```

## Step 4: Configure DNS
After running the script, you'll get a target domain. Create a CNAME record:

```
Type: CNAME
Name: api.yourdomain.com
Value: [TARGET_DOMAIN_FROM_SCRIPT]
TTL: 300
```

## Step 5: Update Frontend Configuration
Update your frontend environment variables:

```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_API_KEY=XEbkTgkkhF8zrwu4KyYwm6mZTsXpHVxF6ub6lVux
```

## Step 6: Test Custom Domain
```bash
curl -X POST https://api.yourdomain.com/ai/cv/tailor \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: XEbkTgkkhF8zrwu4KyYwm6mZTsXpHVxF6ub6lVux' \
  -d '{"job_description": "test", "user_cv_text": "test"}'
```

## Troubleshooting

### Certificate Issues
- Ensure certificate is in `us-east-1` region
- Verify certificate is validated and active
- Check domain name matches exactly

### DNS Issues
- Verify CNAME record is correct
- Wait for DNS propagation (5-10 minutes)
- Use `dig` or `nslookup` to verify DNS resolution

### API Gateway Issues
- Check API Gateway custom domain configuration
- Verify base path mapping is correct
- Ensure API is deployed to the correct stage

## Current Configuration
- **API Gateway ID**: wz2lhr4qzk
- **Current URL**: https://wz2lhr4qzk.execute-api.eu-north-1.amazonaws.com/prod
- **API Key**: XEbkTgkkhF8zrwu4KyYwm6mZTsXpHVxF6ub6lVux
- **Rate Limits**: 100 burst, 50 sustained, 10,000 daily quota

## Security Considerations
1. **API Key Management**: Store API keys securely, rotate regularly
2. **HTTPS Only**: Always use HTTPS for API calls
3. **Rate Limiting**: Monitor usage and adjust limits as needed
4. **Access Logs**: Enable CloudWatch logs for monitoring

## Monitoring
- CloudWatch alarms are configured for throttling and high request counts
- Monitor API Gateway metrics in CloudWatch console
- Set up billing alerts for unexpected usage

## Support
For issues with custom domain setup, check:
1. AWS API Gateway documentation
2. AWS Certificate Manager documentation
3. Your DNS provider's documentation
