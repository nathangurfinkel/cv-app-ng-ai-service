"""
SQS worker Lambda handler for async jobs.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .core.config import settings
from .models.job_models import JobStatus
from .services.ai_service import AIService
from .services.data_transformation_service import DataTransformationService
from .services.dynamo_job_repository import DynamoJobRepository


_ai_service: AIService | None = None
_transformer: DataTransformationService | None = None
_repo: DynamoJobRepository | None = None


def _get_repo() -> DynamoJobRepository:
    global _repo
    if _repo is None:
        if not settings.JOBS_TABLE_NAME:
            raise RuntimeError("JOBS_TABLE_NAME is not configured")
        _repo = DynamoJobRepository(settings.JOBS_TABLE_NAME)
    return _repo


def _get_ai() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def _get_transformer() -> DataTransformationService:
    global _transformer
    if _transformer is None:
        _transformer = DataTransformationService()
    return _transformer


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda SQS handler.
    """
    repo = _get_repo()
    ai = _get_ai()
    transformer = _get_transformer()

    records = event.get("Records", []) or []
    processed = 0

    for r in records:
        processed += 1
        body = r.get("body") or "{}"
        msg = json.loads(body)
        job_id = msg.get("job_id")
        job_type = msg.get("job_type")

        if not job_id:
            continue

        item = repo.get_job(job_id)
        if not item:
            continue

        if item.get("status") == JobStatus.cancelled.value:
            continue

        try:
            repo.update_status(job_id=job_id, status=JobStatus.processing)
            payload = item.get("payload") or {}

            if job_type == "extract":
                cv_text = payload.get("cv_text", "")
                job_description = payload.get("job_description", "")
                raw_ai_data = ai.extract_structured_cv_data(cv_text, job_description)  # type: ignore[call-arg]
                # ai.extract_structured_cv_data is async; run it in sync context
                # by using asyncio.run for Lambda worker.
                import asyncio

                raw_ai_data = asyncio.run(raw_ai_data)
                cv_data = transformer.transform_ai_data_to_cv_data(raw_ai_data)
                structured_content = transformer.cv_data_to_dict(cv_data)
                repo.update_status(job_id=job_id, status=JobStatus.succeeded, result=structured_content)
            else:
                repo.update_status(
                    job_id=job_id,
                    status=JobStatus.failed,
                    error_code="unsupported_job_type",
                    error_message=f"Unsupported job_type: {job_type}",
                )

        except Exception as e:
            repo.update_status(
                job_id=job_id,
                status=JobStatus.failed,
                error_code="worker_error",
                error_message=str(e),
            )

    return {"processed": processed}

