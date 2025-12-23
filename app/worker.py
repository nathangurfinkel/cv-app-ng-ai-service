"""
SQS worker Lambda handler for async jobs.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .core.config import settings
from .models.job_models import JobStatus, JobType
from .services.ai_service import AIService
from .services.data_transformation_service import DataTransformationService
from .services.dynamo_job_repository import DynamoJobRepository
from .services.evaluation_service import EvaluationService
from .utils.security import validate_cv_text, validate_job_description


_ai_service: AIService | None = None
_transformer: DataTransformationService | None = None
_evaluation: EvaluationService | None = None
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


def _get_evaluation(ai: AIService) -> EvaluationService:
    global _evaluation
    if _evaluation is None:
        _evaluation = EvaluationService(ai)
    return _evaluation


def _run_async(coro: Any) -> Any:
    import asyncio

    return asyncio.run(coro)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda SQS handler.
    """
    repo = _get_repo()
    ai = _get_ai()
    transformer = _get_transformer()
    evaluation = _get_evaluation(ai)

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

            if job_type == JobType.extract.value:
                cv_text = payload.get("cv_text", "")
                job_description = payload.get("job_description", "")
                raw_ai_data = _run_async(ai.extract_structured_cv_data(cv_text, job_description))  # type: ignore[call-arg]
                cv_data = transformer.transform_ai_data_to_cv_data(raw_ai_data)
                structured_content = transformer.cv_data_to_dict(cv_data)
                repo.update_status(job_id=job_id, status=JobStatus.succeeded, result=structured_content)
            elif job_type == JobType.tailor.value:
                user_cv_text = validate_cv_text(payload.get("user_cv_text", ""))
                jd = validate_job_description(payload.get("job_description", ""))

                raw_ai_data = _run_async(ai.extract_structured_cv_data(user_cv_text, jd))  # type: ignore[call-arg]
                cv_data = transformer.transform_ai_data_to_cv_data(raw_ai_data)
                structured_content = transformer.cv_data_to_dict(cv_data)

                # Attach analysis (can be slow) but worker timeout handles it.
                analysis = _run_async(evaluation.evaluate_cv_complete(jd, json.dumps(structured_content), []))
                structured_content["analysis"] = analysis

                repo.update_status(job_id=job_id, status=JobStatus.succeeded, result=structured_content)
            elif job_type == JobType.evaluate.value:
                jd = validate_job_description(payload.get("job_description", ""))
                cv_json = payload.get("cv_json") or {}
                cv_content_str = json.dumps(cv_json, indent=2)
                committee_analysis = _run_async(evaluation.evaluate_cv_with_committee(jd, cv_content_str))
                repo.update_status(job_id=job_id, status=JobStatus.succeeded, result=committee_analysis)
            elif job_type == JobType.rephrase.value:
                section_content = payload.get("section_content", "")
                section_type = payload.get("section_type", "")
                jd = validate_job_description(payload.get("job_description", ""))
                rephrased_content = _run_async(ai.rephrase_cv_section(section_content, section_type, jd))
                repo.update_status(
                    job_id=job_id,
                    status=JobStatus.succeeded,
                    result={
                        "original_content": section_content,
                        "rephrased_content": rephrased_content,
                        "section_type": section_type,
                    },
                )
            elif job_type == JobType.recommend.value:
                jd = validate_job_description(payload.get("job_description", ""))
                cv_data = payload.get("cv_data") or {}
                recommendation = _run_async(ai.recommend_template(jd, cv_data))
                repo.update_status(job_id=job_id, status=JobStatus.succeeded, result=recommendation)
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

