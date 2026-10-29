"""Telegram webhook Lambda.

Its only jobs: check the request really comes from Telegram, drop users
who are not on the allowlist, put the update on the SQS queue, and
answer HTTP 200 fast. All slow work happens in the worker.

Telegram retries an update if it doesn't get a 2xx, so we return 200
even for updates we ignore.
"""

from __future__ import annotations

import hmac
import json
from functools import lru_cache
from typing import Any

from shared.config import allowed_user_ids, env, telegram_secrets
from shared.log import get_logger, log
from shared.telegram import parse_update

logger = get_logger("webhook")

SECRET_HEADER = "x-telegram-bot-api-secret-token"  # noqa: S105 header name, not a secret


@lru_cache(maxsize=1)
def _sqs() -> Any:
    import boto3

    return boto3.client("sqs")


def _response(status: int, body: str = "ok") -> dict[str, Any]:
    return {"statusCode": status, "body": body}


def _header(event: dict[str, Any], name: str) -> str:
    headers = event.get("headers") or {}
    # HTTP API v2 lower-cases header names, but be defensive.
    for key, value in headers.items():
        if key.lower() == name:
            return str(value)
    return ""


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    expected = telegram_secrets()["webhook_secret"]
    if not hmac.compare_digest(_header(event, SECRET_HEADER), expected):
        log(logger, "rejected: bad secret token")
        return _response(401, "unauthorized")

    try:
        update = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        log(logger, "rejected: invalid JSON")
        return _response(400, "bad request")

    message = parse_update(update)
    if message is None:
        log(logger, "ignored update", update_id=update.get("update_id"))
        return _response(200)

    if message.user_id not in allowed_user_ids():
        # Not processed, not stored: only an anonymous log line.
        log(logger, "dropped: user not on allowlist", update_id=message.update_id)
        return _response(200)

    _sqs().send_message(QueueUrl=env("QUEUE_URL"), MessageBody=json.dumps(update))
    log(logger, "queued", update_id=message.update_id, kind=message.kind)
    return _response(200)
