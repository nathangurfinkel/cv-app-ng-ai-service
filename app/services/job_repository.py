"""
Job repository abstraction (SRP + DIP).

This keeps persistence details (DynamoDB) out of route handlers and workers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..models.job_models import JobStatus


class JobRepository(ABC):
    @abstractmethod
    def create_job(
        self,
        *,
        job_id: str,
        job_type: str,
        status: JobStatus,
        ttl_epoch_seconds: int,
    ) -> None:
        """
        Create a job record (metadata only, no payload).
        Payload is sent via JobQueue to avoid storing sensitive data in DB.
        """
        raise NotImplementedError

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self,
        *,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        raise NotImplementedError


