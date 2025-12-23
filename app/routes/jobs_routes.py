"""
Async job routes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.config import settings
from ..models.job_models import ExtractJobCreateRequest, JobCreateResponse, JobError, JobStatus, JobStatusResponse
from ..services.dynamo_job_repository import DynamoJobRepository
from ..services.jobs_service import JobsService
from ..services.sqs_job_queue import SqsJobQueue

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_jobs_service() -> JobsService:
    if not settings.JOBS_TABLE_NAME or not settings.JOBS_QUEUE_URL:
        raise HTTPException(status_code=500, detail="Jobs infrastructure is not configured")
    return JobsService(
        repository=DynamoJobRepository(settings.JOBS_TABLE_NAME),
        queue=SqsJobQueue(settings.JOBS_QUEUE_URL),
        ttl_hours=settings.JOB_TTL_HOURS,
    )


@router.post("/extract", status_code=202, response_model=JobCreateResponse)
def create_extract_job(request: ExtractJobCreateRequest) -> JobCreateResponse:
    svc = _get_jobs_service()
    job_id = svc.create_extract_job(cv_text=request.cv_text, job_description=request.job_description)
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
        error = JobError(code=error_code or "unknown", message=error_message or "Unknown error")

    return JobStatusResponse(job_id=job_id, status=status, result=result, error=error)


@router.delete("/{job_id}", response_model=JobStatusResponse)
def cancel_job(job_id: str) -> JobStatusResponse:
    svc = _get_jobs_service()
    ok = svc.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    item = svc.get_job(job_id) or {"status": JobStatus.cancelled.value}
    return JobStatusResponse(job_id=job_id, status=JobStatus(item["status"]))

