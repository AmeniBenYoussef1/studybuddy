"""Worker Lambda: consumes the SQS queue and replies on Telegram.

Week 1 behaviour is an "echo" bot that proves the full pipeline works.
From week 2 the `respond` function will call the AgentCore agent instead.

Idempotency: Telegram may deliver the same update twice, and SQS may
deliver a message twice. We record each update_id in DynamoDB with a
conditional write; a second delivery fails the condition and is skipped.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any

from shared.config import env, telegram_secrets
from shared.log import get_logger, log
from shared.telegram import IncomingMessage, TelegramClient, parse_update

logger = get_logger("worker")

DEDUP_TTL_SECONDS = 24 * 3600

HELP_TEXT = (
    "Hi! I'm StudyBuddy, your study assistant (week-1 preview).\n\n"
    "Right now I just echo what you send, to test that everything works.\n"
    "Commands: /start, /help"
)


@lru_cache(maxsize=1)
def _dynamodb() -> Any:
    import boto3

    return boto3.client("dynamodb")


@lru_cache(maxsize=1)
def _telegram() -> TelegramClient:
    return TelegramClient(telegram_secrets()["bot_token"])


def first_time_seen(update_id: int) -> bool:
    """Record update_id; return False if it was already processed."""
    from botocore.exceptions import ClientError

    try:
        _dynamodb().put_item(
            TableName=env("DEDUP_TABLE"),
            Item={
                "update_id": {"N": str(update_id)},
                "expires_at": {"N": str(int(time.time()) + DEDUP_TTL_SECONDS)},
            },
            ConditionExpression="attribute_not_exists(update_id)",
        )
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def respond(message: IncomingMessage) -> str:
    """Build the reply text. Pure function: easy to unit-test."""
    if message.kind == "text" and message.text is not None:
        command = message.text.strip().split()[0].lower() if message.text.strip() else ""
        if command in ("/start", "/help"):
            return HELP_TEXT
        return f"You said: {message.text}"
    if message.kind == "voice":
        return "I received your voice note. (Transcription arrives in week 3.)"
    if message.kind == "photo":
        return "I received your photo. (Image understanding arrives in week 3.)"
    if message.kind == "document":
        name = message.file_name or "your file"
        return f"I received {name}. (Course indexing arrives in week 4.)"
    return "Sorry, I can't handle that kind of message yet."


def process_record(record: dict[str, Any]) -> None:
    update = json.loads(record["body"])
    message = parse_update(update)
    if message is None:
        return
    if not first_time_seen(message.update_id):
        log(logger, "duplicate skipped", update_id=message.update_id)
        return

    started = time.monotonic()
    reply = respond(message)
    _telegram().send_message(message.chat_id, reply)
    log(
        logger,
        "replied",
        update_id=message.update_id,
        kind=message.kind,
        latency_ms=round((time.monotonic() - started) * 1000),
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """SQS batch handler with partial-batch failure reporting.

    Only the failed messages are retried (and land in the DLQ after
    max retries); successful ones are not reprocessed.
    """
    failures: list[dict[str, str]] = []
    for record in event.get("Records", []):
        try:
            process_record(record)
        except Exception:
            logger.exception("failed to process record")
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
