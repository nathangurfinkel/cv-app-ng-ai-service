"""
DynamoDB implementation of JobRepository.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import boto3
from decimal import Decimal

from ..models.job_models import JobStatus
from .job_repository import JobRepository


def _to_dynamo_compatible(value: Any) -> Any:
    """
    Recursively convert Python values into DynamoDB-compatible values.

    DynamoDB (via boto3) does not accept float types; use Decimal instead.
    We convert floats to Decimal using string conversion to avoid binary float artifacts.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return [_to_dynamo_compatible(v) for v in value]
    if isinstance(value, tuple):
        return [_to_dynamo_compatible(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_dynamo_compatible(v) for k, v in value.items()}
    return str(value)


class DynamoJobRepository(JobRepository):
    def __init__(self, table_name: str):
        self._table = boto3.resource("dynamodb").Table(table_name)

    def create_job(
        self,
        *,
        job_id: str,
        job_type: str,
        status: JobStatus,
        payload: Dict[str, Any],
        ttl_epoch_seconds: int,
    ) -> None:
        now = int(time.time())
        self._table.put_item(
            Item={
                "job_id": job_id,
                "job_type": job_type,
                "status": status.value,
                "payload": _to_dynamo_compatible(payload),
                "created_at": now,
                "updated_at": now,
                "ttl": ttl_epoch_seconds,
            }
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        resp = self._table.get_item(Key={"job_id": job_id})
        return resp.get("Item")

    def update_status(
        self,
        *,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        now = int(time.time())
        expr = ["#s = :s", "updated_at = :u"]
        names = {"#s": "status"}
        values: Dict[str, Any] = {":s": status.value, ":u": now}

        if result is not None:
            expr.append("#r = :r")
            names["#r"] = "result"
            values[":r"] = _to_dynamo_compatible(result)
            # clear error fields on success
            expr.append("error_code = :ec")
            expr.append("error_message = :em")
            values[":ec"] = None
            values[":em"] = None

        if error_code is not None or error_message is not None:
            expr.append("error_code = :ec")
            expr.append("error_message = :em")
            values[":ec"] = error_code
            values[":em"] = error_message

        self._table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET " + ", ".join(expr),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

