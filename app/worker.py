"""
SQS worker Lambda handler for async jobs with BYOK support.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .core.config import settings
from .models.job_models import JobStatus, JobType
from .services.ai_service import AIService
from .services.data_transformation_service import DataTransformationService
from .services.dynamo_job_repository import DynamoJobRepository
from .services.evaluation_service import EvaluationService
from .utils.security import validate_cv_text, validate_job_description


_transformer: DataTransformationService | None = None
_repo: DynamoJobRepository | None = None


def _get_repo() -> DynamoJobRepository:
    global _repo
    if _repo is None:
        if not settings.JOBS_TABLE_NAME:
            raise RuntimeError("JOBS_TABLE_NAME is not configured")
        endpoint_url = settings.AWS_ENDPOINT_URL if settings.AWS_ENDPOINT_URL else None
        _repo = DynamoJobRepository(settings.JOBS_TABLE_NAME, endpoint_url=endpoint_url)
    return _repo


def _get_transformer() -> DataTransformationService:
    global _transformer
    if _transformer is None:
        _transformer = DataTransformationService()
    return _transformer


def _create_ai_service(
    user_provider: Optional[str],
    user_api_key: Optional[str],
    user_tier: Optional[str],
) -> AIService:
    """
    Create AIService with BYOK support. Only uses system OpenAI key for verified MANAGED tier.
    
    Args:
        user_provider: User's AI provider (openai or gemini)
        user_api_key: User's API key
        user_tier: Verified user tier (from server-side validation)
        
    Returns:
        AIService instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    # BYOK path: user provided both provider and key
    if user_provider and user_api_key:
        return AIService(provider=user_provider, api_key=user_api_key)
    
    # MANAGED tier: use system OpenAI key (only if tier is verified MANAGED)
    if user_tier == "managed_subscription":
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "System OPENAI_API_KEY is not configured for Managed tier. "
                "Please configure OPENAI_API_KEY environment variable."
            )
        return AIService(provider="openai", api_key=None)  # Will use settings.OPENAI_API_KEY
    
    # No user key and not MANAGED tier: require BYOK
    raise ValueError(
        "BYOK required: X-User-Provider and X-User-Api-Key headers are required "
        "for this tier. Managed tier subscriptions must be verified server-side."
    )


def _run_async(coro: Any) -> Any:
    import asyncio

    return asyncio.run(coro)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda SQS handler with BYOK support.
    """
    repo = _get_repo()
    transformer = _get_transformer()

    records = event.get("Records", []) or []
    processed = 0

    for r in records:
        processed += 1
        body = r.get("body") or "{}"
        msg = json.loads(body)
        job_id = msg.get("job_id")
        job_type = msg.get("job_type")
        
        # Extract BYOK and tier from SQS message (set by routes via JobsService -> SqsJobQueue)
        user_provider = msg.get("user_provider")
        user_api_key = msg.get("user_api_key")
        user_tier = msg.get("user_tier")
        
        # Extract payload from SQS message (NOT from DynamoDB)
        # Privacy: payload is ephemeral (only in SQS, not persisted in DB)
        # Plan: local-first_vault_c7381a99
        payload = msg.get("payload") or {}

        if not job_id:
            continue

        item = repo.get_job(job_id)
        if not item:
            continue

        if item.get("status") == JobStatus.cancelled.value:
            continue

        try:
            # Create AI service with BYOK or system key (only for verified MANAGED tier)
            ai = _create_ai_service(user_provider, user_api_key, user_tier)
            evaluation = EvaluationService(ai)
            
            repo.update_status(job_id=job_id, status=JobStatus.processing)

            if job_type == JobType.extract.value:
                cv_text = payload.get("cv_text", "")
                job_description = payload.get("job_description", "")
                # Pass None if job_description is empty string
                job_description_or_none = job_description if job_description and job_description.strip() else None
                raw_ai_data = _run_async(ai.extract_structured_cv_data(cv_text, job_description_or_none))  # type: ignore[call-arg]
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
            elif job_type == JobType.inject_keyword.value:
                section_content = payload.get("section_content", "")
                section_type = payload.get("section_type", "")
                keyword = payload.get("keyword", "")
                jd = validate_job_description(payload.get("job_description", ""))
                result = _run_async(ai.inject_keyword(section_content, section_type, keyword, jd))
                # Check if result is REQUIRES_CONTEXT
                if result == "REQUIRES_CONTEXT":
                    repo.update_status(
                        job_id=job_id,
                        status=JobStatus.succeeded,
                        result={"requires_context": True},
                    )
                else:
                    repo.update_status(
                        job_id=job_id,
                        status=JobStatus.succeeded,
                        result={
                            "rephrased_content": result,
                            "requires_context": False,
                        },
                    )
            elif job_type == JobType.elaborate.value:
                section_content = payload.get("section_content", "")
                section_type = payload.get("section_type", "")
                keyword = payload.get("keyword", "")
                user_context = payload.get("user_context", "")
                jd = validate_job_description(payload.get("job_description", ""))
                rephrased_content = _run_async(ai.elaborate_with_keyword(section_content, section_type, keyword, user_context, jd))
                repo.update_status(
                    job_id=job_id,
                    status=JobStatus.succeeded,
                    result={
                        "rephrased_content": rephrased_content,
                    },
                )
            else:
                repo.update_status(
                    job_id=job_id,
                    status=JobStatus.failed,
                    error_code="unsupported_job_type",
                    error_message=f"Unsupported job_type: {job_type}",
                )

        except ValueError as e:
            # Configuration errors (missing keys, invalid provider)
            repo.update_status(
                job_id=job_id,
                status=JobStatus.failed,
                error_code="configuration_error",
                error_message=str(e),
            )
        except Exception as e:
            # General worker errors
            repo.update_status(
                job_id=job_id,
                status=JobStatus.failed,
                error_code="worker_error",
                error_message=str(e),
            )

    return {"processed": processed}

