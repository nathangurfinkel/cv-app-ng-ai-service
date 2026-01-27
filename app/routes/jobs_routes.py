"""
Async job routes.
"""

from __future__ import annotations
import logging

from fastapi import APIRouter, Header, HTTPException, Depends

from ..core.config import settings

logger = logging.getLogger(__name__)
from ..models.job_models import (
    ElaborateJobCreateRequest,
    EvaluateJobCreateRequest,
    ExtractJobCreateRequest,
    ImproveFromFeedbackJobCreateRequest,
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
    try:
        return JobsService(
            repository=DynamoJobRepository(settings.JOBS_TABLE_NAME, endpoint_url=endpoint_url),
            queue=SqsJobQueue(settings.JOBS_QUEUE_URL, endpoint_url=endpoint_url),
            ttl_hours=settings.JOB_TTL_HOURS,
        )
    except Exception as e:
        logger.exception("Failed to initialize JobsService")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize jobs infrastructure: {str(e)}. Check AWS credentials and service availability."
        )


@router.post("/extract", status_code=202, response_model=JobCreateResponse)
def create_extract_job(
    request: ExtractJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    try:
        logger.info("[JOB_ROUTE] Creating extract job", extra={
            "cv_text_length": len(request.cv_text),
            "cv_text_preview": request.cv_text[:200] + ("..." if len(request.cv_text) > 200 else ""),
            "has_job_description": bool(request.job_description),
            "job_description_length": len(request.job_description) if request.job_description else 0,
            "user_tier": tier.value,
            "has_user_provider": bool(x_user_provider),
            "timestamp": __import__("datetime").datetime.now().isoformat()
        })
        
        svc = _get_jobs_service()
        job_id = svc.create_extract_job(
            cv_text=request.cv_text,
            job_description=request.job_description,
            user_provider=x_user_provider,
            user_api_key=x_user_api_key,
            user_tier=tier.value,
        )
        
        logger.info("[JOB_ROUTE] Extract job created successfully", extra={
            "job_id": job_id,
            "status": JobStatus.queued.value
        })
        # #region agent log
        try:
            with open("/Users/nathangurfinkel/repos/cv-app-ng-frontend/.cursor/debug.log", "a") as f:
                f.write(json.dumps({"location": "jobs_routes:create_extract_job", "message": "job_created", "data": {"job_id": job_id}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": "H4"}) + "\n")
        except Exception:
            pass
        # #endregion
        return JobCreateResponse(job_id=job_id, status=JobStatus.queued)
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        # Log the full exception for debugging
        logger.exception("Failed to create extract job", extra={
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create extract job: {str(e)}"
        )


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
        instruction_type=request.instruction_type,
        custom_instruction=request.custom_instruction,
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


@router.post("/improve-from-feedback", status_code=202, response_model=JobCreateResponse)
def create_improve_from_feedback_job(
    request: ImproveFromFeedbackJobCreateRequest,
    x_user_provider: str | None = Header(default=None, alias="X-User-Provider"),
    x_user_api_key: str | None = Header(default=None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_ai_operations),
) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_improve_from_feedback_job(
        cv_json=request.cv_json,
        job_description=request.job_description,
        persona_feedback=request.persona_feedback,
        user_responses=request.user_responses,
        target_section=request.target_section,
        section_context=request.section_context,
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

