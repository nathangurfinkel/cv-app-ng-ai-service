"""API routes for AI service."""
from .cv_routes import router as cv_router
from .evaluation_routes import router as evaluation_router

__all__ = ["cv_router", "evaluation_router"]
