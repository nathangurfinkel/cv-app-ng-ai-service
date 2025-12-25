"""
SQS implementation of JobQueue.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import boto3

from .job_queue import JobQueue


class SqsJobQueue(JobQueue):
    def __init__(self, queue_url: str, endpoint_url: str | None = None):
        self._queue_url = queue_url
        sqs_kwargs = {}
        if endpoint_url:
            sqs_kwargs["endpoint_url"] = endpoint_url
        self._client = boto3.client("sqs", **sqs_kwargs)

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
        Enqueue job with payload in SQS message body.
        
        Privacy: payload is processed by worker but NOT persisted in DynamoDB.
        This ensures CV/job data is ephemeral (TTL via SQS retention only).
        
        Plan: local-first_vault_c7381a99
        """
        body: dict[str, object] = {
            "job_id": job_id,
            "job_type": job_type,
            "payload": payload,
        }
        if user_provider:
            body["user_provider"] = user_provider
        if user_api_key:
            body["user_api_key"] = user_api_key
        if user_tier:
            body["user_tier"] = user_tier
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(body),
        )


