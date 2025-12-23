"""
Job queue abstraction (SRP + DIP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class JobQueue(ABC):
    @abstractmethod
    def enqueue(self, *, job_id: str, job_type: str) -> None:
        raise NotImplementedError

