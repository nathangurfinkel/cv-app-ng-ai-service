"""
Configuration management for the CV Builder application.
Handles environment variables and application settings.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    
    # Template Configuration
    TEMPLATES_DIR: str = "./templates"
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET", "")
    
    # Lambda Configuration
    IS_LAMBDA: bool = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
    
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

# Global settings instance
settings = Settings()
