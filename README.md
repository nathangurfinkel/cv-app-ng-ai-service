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

## Environment Variables

Create a `.env` file with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Configuration (optional)
PINECONE_API_KEY=your_pinecone_api_key_here
MOCK_PINECONE=true

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com

# Debug Configuration
DEBUG=false
VERBOSE=false
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your actual values
```

3. Run locally:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Deployment to AWS Lambda

1. Package the application:
```bash
pip install -r requirements.txt -t .
zip -r ai-service.zip .
```

2. Deploy to AWS Lambda using AWS CLI or console
3. Configure API Gateway to route `/ai/*` requests to this Lambda function

## API Endpoints

- `GET /` - Health check
- `GET /health` - Health check
- `POST /ai/cv/tailor` - Tailor CV from text
- `POST /ai/cv/tailor-from-file` - Tailor CV from uploaded file
- `POST /ai/cv/extract-cv-data` - Extract structured CV data
- `POST /ai/cv/rephrase-section` - Rephrase CV section
- `POST /ai/cv/recommend-template` - Recommend CV template
- `POST /ai/evaluation/cv` - Evaluate CV
