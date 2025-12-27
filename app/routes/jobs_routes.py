"""
Async job routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Depends

from ..core.config import settings
from ..models.job_models import (
    ElaborateJobCreateRequest,
    EvaluateJobCreateRequest,
    ExtractJobCreateRequest,
    InjectKeywordJobCreateRequest,
    JobCreateResponse,
    JobError,
    JobStatus,
    JobStatusResponse,
    RecommendJobCreateRequest,
    RephraseJobCreateRequest,
    TailorJobCreateRequest,
)
from ..services.dynamo_job_repository import DynamoJobRepository
from ..services.jobs_service import JobsService
from ..services.sqs_job_queue import SqsJobQueue
from ..utils.tier_validation import require_ai_operations, UserTier

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_jobs_service() -> JobsService:
    missing = []
    if not settings.JOBS_TABLE_NAME:
        missing.append("JOBS_TABLE_NAME")
    if not settings.JOBS_QUEUE_URL:
        missing.append("JOBS_QUEUE_URL")
    if missing:
        raise HTTPException(
            status_code=500, 
            detail=f"Jobs infrastructure is not configured. Missing environment variables: {', '.join(missing)}. Please set these in your .env file or environment."
        )
    endpoint_url = settings.AWS_ENDPOINT_URL if settings.AWS_ENDPOINT_URL else None
    return JobsService(
        repository=DynamoJobRepository(settings.JOBS_TABLE_NAME, endpoint_url=endpoint_url),
        queue=SqsJobQueue(settings.JOBS_QUEUE_URL, endpoint_url=endpoint_url),
        ttl_hours=settings.JOB_TTL_HOURS,
    )


@router.post("/extract", status_code=202, response_model=JobCreateResponse)
def create_extract_job(
    request: ExtractJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_extract_job(
        cv_text=request.cv_text,
        job_description=request.job_description,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.post("/tailor", status_code=202, response_model=JobCreateResponse)
def create_tailor_job(
    request: TailorJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_tailor_job(
        user_cv_text=request.user_cv_text,
        job_description=request.job_description,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.post("/evaluate", status_code=202, response_model=JobCreateResponse)
def create_evaluate_job(
    request: EvaluateJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_evaluate_job(
        job_description=request.job_description,
        cv_json=request.cv_json,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.post("/rephrase", status_code=202, response_model=JobCreateResponse)
def create_rephrase_job(
    request: RephraseJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_rephrase_job(
        section_content=request.section_content,
        section_type=request.section_type,
        job_description=request.job_description,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.post("/recommend", status_code=202, response_model=JobCreateResponse)
def create_recommend_job(
    request: RecommendJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_recommend_job(
        job_description=request.job_description,
        cv_data=request.cv_data,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.post("/inject-keyword", status_code=202, response_model=JobCreateResponse)
def create_inject_keyword_job(
    request: InjectKeywordJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_inject_keyword_job(
        section_content=request.section_content,
        section_type=request.section_type,
        keyword=request.keyword,
        job_description=request.job_description,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.post("/elaborate", status_code=202, response_model=JobCreateResponse)
def create_elaborate_job(
    request: ElaborateJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_elaborate_job(
        section_content=request.section_content,
        section_type=request.section_type,
        keyword=request.keyword,
        user_context=request.user_context,
        job_description=request.job_description,
        user_provider=x_user_provider,
        user_api_key=x_user_api_key,
        user_tier=tier.value,
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    svc = _get_jobs_service()
    item = svc.get_job(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")

    status = JobStatus(item["status"])
    result = item.get("result")
    error_code = item.get("error_code")
    error_message = item.get("error_message")
    error = None
    if error_code or error_message:
        # Both fields are optional in JobError model to match frontend expectations
        error = JobError(code=error_code, message=error_message)

    return JobStatusResponse(job_id=job_id, status=status, result=result, error=error)


@router.delete("/{job_id}", response_model=JobStatusResponse)
def cancel_job(job_id: str) -> JobStatusResponse:
    svc = _get_jobs_service()
    ok = svc.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    item = svc.get_job(job_id) or {"status": JobStatus.cancelled.value}
    return JobStatusResponse(job_id=job_id, status=JobStatus(item["status"]))

