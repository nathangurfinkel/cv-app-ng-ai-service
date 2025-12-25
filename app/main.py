"""
Main FastAPI application entry point for AI Service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from .core.config import settings
from .routes import cv_router, evaluation_router, jobs_router
from .routes.webhooks_routes import router as webhooks_router
from .routes.roast_routes import router as roast_router
from .routes.interview_routes import router as interview_router
from .utils.debug import print_step

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="CV Builder AI Service",
        version="1.0.0",
        description="AI Service for CV generation, evaluation, and recommendations",
        debug=settings.DEBUG
    )
    
    # Add CORS middleware
    print_step("CORS Configuration", {"origins": settings.CORS_ORIGINS}, "input")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALL_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        # Frontend sends these headers (API auth + BYOK). Must be explicitly allowlisted for CORS preflight.
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-User-Provider",
            "X-User-Api-Key",
            "X-User-Tier",
            "X-License-Key",
        ],
    )
    print_step("FastAPI App Initialization", "FastAPI app and CORS middleware configured", "output")
    
    # Include routers with /ai prefix
    app.include_router(cv_router, prefix="/ai")
    app.include_router(evaluation_router, prefix="/ai")
    app.include_router(jobs_router, prefix="/ai")
    app.include_router(webhooks_router, prefix="/ai")
    app.include_router(roast_router, prefix="/ai")
    app.include_router(interview_router, prefix="/ai")
    
    # Root endpoint
    @app.get("/")
    def read_root():
        return {"status": "CV Builder AI Service is online"}
    
    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "healthy", "service": "ai-service"}
    
    return app

# Create the app instance
app = create_app()

# Create Mangum handler for AWS Lambda
handler = Mangum(app)

# Application startup message
print_step("Application Startup", "CV Builder AI Service is ready to serve requests!", "output")
print("\n" + "="*80)
print("CV BUILDER AI SERVICE STARTED SUCCESSFULLY")
print("="*80)
print("Available Endpoints:")
print("   • GET  /                    - Health check")
print("   • GET  /health              - Health check")
print("   • POST /ai/extract-cv-data  - Extract data from CV files")
print("   • POST /ai/tailor-cv        - Tailor CV from text")
print("   • POST /ai/tailor-cv-from-file - Tailor CV from uploaded file")
print("   • POST /ai/evaluate-cv      - Perform committee evaluation on a generated CV")
print("   • POST /ai/rephrase-section - Rephrase CV sections")
print("   • POST /ai/get-template-recommendation - Get template recommendations")
print("="*80)
print("Debug Mode: ENABLED - Detailed logging will be shown for each request")
print("="*80 + "\n")