"""
Request models for API endpoints.
"""
from pydantic import BaseModel
from typing import Dict, Any

class CVRequest(BaseModel):
    """CV tailoring request model."""
    job_description: str
    user_cv_text: str

class ImageRequest(BaseModel):
    """Image analysis request model."""
    image_base_64: str

class EvaluationRequest(BaseModel):
    """CV evaluation request model."""
    job_description: str
    cv_json: Dict[str, Any]

class ExtractCVRequest(BaseModel):
    """CV extraction request model."""
    cv_text: str
    job_description: str

class RephraseRequest(BaseModel):
    """CV section rephrase request model."""
    section_content: str
    section_type: str
    job_description: str

class TemplateRecommendationRequest(BaseModel):
    """Template recommendation request model."""
    job_description: str
    cv_data: Dict[str, Any]
