"""
Async jobs orchestration (create + poll + cancel).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from ..models.job_models import JobStatus, JobType
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

    def create_extract_job(self, *, cv_text: str, job_description: str) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.extract.value,
            status=JobStatus.queued,
            payload={"cv_text": cv_text, "job_description": job_description},
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(job_id=job_id, job_type=JobType.extract.value)
        return job_id

    def create_tailor_job(self, *, user_cv_text: str, job_description: str) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.tailor.value,
            status=JobStatus.queued,
            payload={"user_cv_text": user_cv_text, "job_description": job_description},
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(job_id=job_id, job_type=JobType.tailor.value)
        return job_id

    def create_evaluate_job(self, *, job_description: str, cv_json: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.evaluate.value,
            status=JobStatus.queued,
            payload={"job_description": job_description, "cv_json": cv_json},
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(job_id=job_id, job_type=JobType.evaluate.value)
        return job_id

    def create_rephrase_job(self, *, section_content: str, section_type: str, job_description: str) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.rephrase.value,
            status=JobStatus.queued,
            payload={
                "section_content": section_content,
                "section_type": section_type,
                "job_description": job_description,
            },
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(job_id=job_id, job_type=JobType.rephrase.value)
        return job_id

    def create_recommend_job(self, *, job_description: str, cv_data: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        ttl = int(time.time()) + int(self._ttl_hours * 3600)
        self._repository.create_job(
            job_id=job_id,
            job_type=JobType.recommend.value,
            status=JobStatus.queued,
            payload={"job_description": job_description, "cv_data": cv_data},
            ttl_epoch_seconds=ttl,
        )
        self._queue.enqueue(job_id=job_id, job_type=JobType.recommend.value)
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

