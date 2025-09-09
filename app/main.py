"""
AI Service FastAPI application entry point for AWS Lambda.
This service handles all AI-related operations including CV generation, evaluation, and utility functions.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from .core.config import settings
from .routes import cv_router, evaluation_router
from .utils.debug import print_step

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application for AI service.
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="CV Builder AI Service",
        version="1.0.0",
        description="AI-powered CV generation, evaluation, and utility services",
        debug=settings.DEBUG
    )
    
    # Add CORS middleware
    print_step("CORS Configuration", {"origins": settings.CORS_ORIGINS}, "input")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALL_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    print_step("FastAPI App Initialization", "FastAPI app and CORS middleware configured", "output")
    
    # Include AI-related routers
    app.include_router(cv_router, prefix="/ai")
    app.include_router(evaluation_router, prefix="/ai")
    
    # Health check endpoint
    @app.get("/")
    def read_root():
        return {"status": "CV Builder AI Service is online", "service": "ai"}
    
    @app.get("/health")
    def health_check():
        return {"status": "healthy", "service": "ai"}
    
    return app

# Create the app instance
app = create_app()

# Mangum handler for AWS Lambda
handler = Mangum(app)

# Application startup message
print_step("AI Service Startup", "CV Builder AI Service is ready to serve requests!", "output")
print("\n" + "="*80)
print("🧠 CV BUILDER AI SERVICE STARTED SUCCESSFULLY")
print("="*80)
print("📋 Available Endpoints:")
print("   • GET  /                    - Health check")
print("   • GET  /health              - Health check")
print("   • POST /ai/cv/tailor        - Tailor CV from text")
print("   • POST /ai/cv/tailor-from-file - Tailor CV from uploaded file")
print("   • POST /ai/cv/extract-cv-data - Extract structured CV data from text")
print("   • POST /ai/cv/rephrase-section - Rephrase CV section")
print("   • POST /ai/cv/recommend-template - Recommend CV template")
print("   • POST /ai/evaluation/cv    - Perform committee evaluation on a generated CV")
print("="*80)
print("🔧 Debug Mode: ENABLED - Detailed logging will be shown for each request")
print("="*80 + "\n")
