"""
Job queue abstraction (SRP + DIP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class JobQueue(ABC):
    @abstractmethod
    def enqueue(
        self,
        *,
        job_id: str,
        job_type: str,
        payload: Dict[str, Any],
        user_provider: str | None = None,
        user_api_key: str | None = None,
        user_tier: str | None = None,
    ) -> None:
        """
        Enqueue a job with its payload.
        The payload contains the sensitive data (CV text, job descriptions) that
        should NOT be persisted in DynamoDB.
        
        Privacy: local-first_vault_c7381a99
        """
        raise NotImplementedError


