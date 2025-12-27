"""
Job-related models for async processing.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class JobType(str, Enum):
    extract = "extract"
    tailor = "tailor"
    evaluate = "evaluate"
    rephrase = "rephrase"
    recommend = "recommend"
    inject_keyword = "inject_keyword"
    elaborate = "elaborate"


class ExtractJobCreateRequest(BaseModel):
    cv_text: str = Field(..., min_length=1)
    job_description: Optional[str] = Field(default="", min_length=0)


class TailorJobCreateRequest(BaseModel):
    user_cv_text: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)


class EvaluateJobCreateRequest(BaseModel):
    job_description: str = Field(..., min_length=1)
    cv_json: Dict[str, Any] = Field(..., min_length=1)  # type: ignore[arg-type]


class RephraseJobCreateRequest(BaseModel):
    section_content: str = Field(..., min_length=1)
    section_type: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)
    instruction_type: Optional[str] = Field(default='default', description="Type of rephrase instruction: 'grammar', 'shorten', 'formal', 'casual', or 'default'")


class RecommendJobCreateRequest(BaseModel):
    job_description: str = Field(..., min_length=1)
    cv_data: Dict[str, Any] = Field(..., min_length=1)  # type: ignore[arg-type]


class InjectKeywordJobCreateRequest(BaseModel):
    section_content: str = Field(..., min_length=1)
    section_type: str = Field(..., min_length=1)
    keyword: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)


class ElaborateJobCreateRequest(BaseModel):
    section_content: str = Field(..., min_length=1)
    section_type: str = Field(..., min_length=1)
    keyword: str = Field(..., min_length=1)
    user_context: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobError(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[JobError] = None

