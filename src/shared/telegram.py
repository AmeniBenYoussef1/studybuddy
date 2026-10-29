"""Minimal Telegram Bot API client and update parsing.

Only the standard library is used, so the Lambda package has no
third-party dependencies.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

API_BASE = "https://api.telegram.org"

MessageKind = Literal["text", "voice", "photo", "document", "other"]


@dataclass(frozen=True)
class IncomingMessage:
    update_id: int
    chat_id: int
    user_id: int
    first_name: str
    kind: MessageKind
    text: str | None = None
    file_id: str | None = None
    file_name: str | None = None


def parse_update(update: dict[str, Any]) -> IncomingMessage | None:
    """Turn a raw Telegram update into an IncomingMessage.

    Returns None for updates we don't handle (edited messages, channel
    posts, callback queries...).
    """
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if "id" not in sender or "id" not in chat:
        return None

    base: dict[str, Any] = {
        "update_id": int(update["update_id"]),
        "chat_id": int(chat["id"]),
        "user_id": int(sender["id"]),
        "first_name": str(sender.get("first_name", "")),
    }

    if "text" in message:
        return IncomingMessage(**base, kind="text", text=str(message["text"]))
    if "voice" in message:
        return IncomingMessage(**base, kind="voice", file_id=message["voice"]["file_id"])
    if message.get("photo"):
        # Telegram sends several sizes; the last one is the largest.
        largest = message["photo"][-1]
        return IncomingMessage(
            **base, kind="photo", file_id=largest["file_id"], text=message.get("caption")
        )
    if "document" in message:
        doc = message["document"]
        return IncomingMessage(
            **base,
            kind="document",
            file_id=doc["file_id"],
            file_name=doc.get("file_name"),
            text=message.get("caption"),
        )
    return IncomingMessage(**base, kind="other")


class TelegramClient:
    def __init__(self, bot_token: str, timeout: float = 10.0) -> None:
        self._base = f"{API_BASE}/bot{bot_token}"
        self._timeout = timeout

    def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        # The URL is always https://api.telegram.org, never user-controlled.
        request = urllib.request.Request(  # noqa: S310
            f"{self._base}/{method}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            body: dict[str, Any] = json.loads(response.read())
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {body.get('description')}")
        return body

    def send_message(self, chat_id: int, text: str) -> None:
        self._call("sendMessage", {"chat_id": chat_id, "text": text})

    def send_typing(self, chat_id: int) -> None:
        self._call("sendChatAction", {"chat_id": chat_id, "action": "typing"})
