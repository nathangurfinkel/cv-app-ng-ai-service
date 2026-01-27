"""
Configuration management for the CV Builder application.
Handles environment variables and application settings.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables. override=True lets .env override inherited
# env (e.g. from dev.sh), so local .env always wins when set.
load_dotenv(override=True)

class Settings:
    """Application settings and configuration."""
    
    # API Configuration
    API_TITLE: str = "CV Builder API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    VERBOSE: bool = os.getenv("VERBOSE", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS Configuration - Restrict to specific domains
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Development only
        "http://127.0.0.1:5173",  # Development only
        # Production domains will be added via environment variables
    ]
    
    # Add production CORS origins from environment
    PRODUCTION_CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
    
    # Combine development and production origins
    ALL_CORS_ORIGINS: List[str] = CORS_ORIGINS + [origin.strip() for origin in PRODUCTION_CORS_ORIGINS if origin.strip()]
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    
    # Pinecone Configuration
    MOCK_PINECONE: bool = os.getenv("MOCK_PINECONE", "true").lower() == "true"
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = "cv-architect-index"
    
    # Lambda Configuration (check first for endpoint URL safety)
    IS_LAMBDA: bool = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    # Force empty endpoint URL in production/Lambda to prevent accidental LocalStack usage
    _endpoint_url_raw = os.getenv("AWS_ENDPOINT_URL", "")
    if ENVIRONMENT == "production" or IS_LAMBDA:
        AWS_ENDPOINT_URL: str = ""
    else:
        AWS_ENDPOINT_URL: str = _endpoint_url_raw
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    # Evaluation Configuration
    EVALUATION_PERSONAS: List[str] = [
        "Strict Hiring Manager",
        "Creative Recruiter", 
        "Senior Technical Lead"
    ]
    
    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_K: int = 7

    # Async Jobs (DynamoDB + SQS)
    JOBS_TABLE_NAME: str = os.getenv("JOBS_TABLE_NAME", "")
    JOBS_QUEUE_URL: str = os.getenv("JOBS_QUEUE_URL", "")
    JOB_TTL_HOURS: int = int(os.getenv("JOB_TTL_HOURS", "24"))
    
    # LemonSqueezy Licensing
    LEMONSQUEEZY_WEBHOOK_SECRET: str = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    LICENSE_SUBSCRIPTIONS_TABLE_NAME: str = os.getenv("LICENSE_SUBSCRIPTIONS_TABLE_NAME", "")

# Global settings instance
settings = Settings()
