"""
SQS implementation of JobQueue.
"""

from __future__ import annotations

import json

import boto3

from .job_queue import JobQueue


class SqsJobQueue(JobQueue):
    def __init__(self, queue_url: str):
        self._queue_url = queue_url
        self._client = boto3.client("sqs")

    def enqueue(self, *, job_id: str, job_type: str) -> None:
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps({"job_id": job_id, "job_type": job_type}),
        )

