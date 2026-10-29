"""Runtime configuration read from environment variables and Secrets Manager.

Secrets are fetched once per Lambda container and cached, so a warm
invocation never calls Secrets Manager again.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def allowed_user_ids() -> frozenset[int]:
    """Telegram user IDs allowed to use the bot (comma-separated in ALLOWED_USER_IDS)."""
    raw = os.environ.get("ALLOWED_USER_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return frozenset(ids)


@lru_cache(maxsize=1)
def _secrets_client() -> Any:
    import boto3  # imported lazily so unit tests don't need AWS

    return boto3.client("secretsmanager")


@lru_cache(maxsize=8)
def get_secret(secret_id: str) -> dict[str, str]:
    """Return a JSON secret from Secrets Manager as a dict (cached per container)."""
    response = _secrets_client().get_secret_value(SecretId=secret_id)
    value: dict[str, str] = json.loads(response["SecretString"])
    return value


def telegram_secrets() -> dict[str, str]:
    """{"bot_token": ..., "webhook_secret": ...}"""
    return get_secret(env("TELEGRAM_SECRET_ARN"))
