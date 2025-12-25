"""
Async jobs orchestration (create + poll + cancel).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from ..models.job_models import JobStatus, JobType
from ..utils.security import validate_sqs_message_size
from .job_queue import JobQueue
from .job_repository import JobRepository


class JobsService:
    def __init__(
        self,
        *,
        repository: JobRepository,
        queue: JobQueue,
        ttl_hours: int,
    ):
        self._repository = repository
        self._queue = queue
        self._ttl_hours = ttl_hours

    def create_extract_job(
        self,
        *,
        cv_text: str,
        job_description: str | None = None,
        user_provider: str | None = None,
        user_api_key: str | None = None,
        user_tier: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        payload = {"cv_text": cv_text, "job_description": job_description or ""}
        
        # Validate payload size before enqueuing
        validate_sqs_message_size(payload)
        
        # Write metadata only to DynamoDB (no payload)
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.extract.value,
            status=JobStatus.queued,
            ttl_epoch_seconds=ttl,
        )
        
        # Send payload via SQS (ephemeral, not persisted in DB)
        self._queue.enqueue(
            job_id=job_id,
            job_type=JobType.extract.value,
            payload=payload,
            user_provider=user_provider,
            user_api_key=user_api_key,
            user_tier=user_tier,
        )
        return job_id

    def create_tailor_job(
        self,
        *,
        user_cv_text: str,
        job_description: str,
        user_provider: str | None = None,
        user_api_key: str | None = None,
        user_tier: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        payload = {"user_cv_text": user_cv_text, "job_description": job_description}
        
        validate_sqs_message_size(payload)
        
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.tailor.value,
            status=JobStatus.queued,
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(
            job_id=job_id,
            job_type=JobType.tailor.value,
            payload=payload,
            user_provider=user_provider,
            user_api_key=user_api_key,
            user_tier=user_tier,
        )
        return job_id

    def create_evaluate_job(
        self,
        *,
        job_description: str,
        cv_json: Dict[str, Any],
        user_provider: str | None = None,
        user_api_key: str | None = None,
        user_tier: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        payload = {"job_description": job_description, "cv_json": cv_json}
        
        validate_sqs_message_size(payload)
        
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.evaluate.value,
            status=JobStatus.queued,
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(
            job_id=job_id,
            job_type=JobType.evaluate.value,
            payload=payload,
            user_provider=user_provider,
            user_api_key=user_api_key,
            user_tier=user_tier,
        )
        return job_id

    def create_rephrase_job(
        self,
        *,
        section_content: str,
        section_type: str,
        job_description: str,
        user_provider: str | None = None,
        user_api_key: str | None = None,
        user_tier: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        payload = {
            "section_content": section_content,
            "section_type": section_type,
            "job_description": job_description,
        }
        
        validate_sqs_message_size(payload)
        
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.rephrase.value,
            status=JobStatus.queued,
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(
            job_id=job_id,
            job_type=JobType.rephrase.value,
            payload=payload,
            user_provider=user_provider,
            user_api_key=user_api_key,
            user_tier=user_tier,
        )
        return job_id

    def create_recommend_job(
        self,
        *,
        job_description: str,
        cv_data: Dict[str, Any],
        user_provider: str | None = None,
        user_api_key: str | None = None,
        user_tier: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        payload = {"job_description": job_description, "cv_data": cv_data}
        
        validate_sqs_message_size(payload)
        
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.recommend.value,
            status=JobStatus.queued,
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(
            job_id=job_id,
            job_type=JobType.recommend.value,
            payload=payload,
            user_provider=user_provider,
            user_api_key=user_api_key,
            user_tier=user_tier,
        )
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._repository.get_job(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self._repository.get_job(job_id)
        if not job:
            return False
        status = job.get("status")
        if status in (JobStatus.succeeded.value, JobStatus.failed.value):
            return True
        self._repository.update_status(job_id=job_id, status=JobStatus.cancelled)
        return True

