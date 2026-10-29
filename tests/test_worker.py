import json
import os
import sys
import types
import unittest
from unittest import mock

from shared.telegram import IncomingMessage
from worker import handler as worker


class FakeClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


# Provide a stand-in for botocore.exceptions so tests run without boto3 installed.
_fake_botocore = types.ModuleType("botocore")
_fake_exceptions = types.ModuleType("botocore.exceptions")
_fake_exceptions.ClientError = FakeClientError  # type: ignore[attr-defined]
_fake_botocore.exceptions = _fake_exceptions  # type: ignore[attr-defined]


def _msg(kind: str, text: str | None = None, file_name: str | None = None) -> IncomingMessage:
    return IncomingMessage(
        update_id=1,
        chat_id=42,
        user_id=42,
        first_name="Ameni",
        kind=kind,  # type: ignore[arg-type]
        text=text,
        file_name=file_name,
    )


class RespondTest(unittest.TestCase):
    def test_echo(self) -> None:
        self.assertEqual(worker.respond(_msg("text", "hello")), "You said: hello")

    def test_start_and_help(self) -> None:
        self.assertEqual(worker.respond(_msg("text", "/start")), worker.HELP_TEXT)
        self.assertEqual(worker.respond(_msg("text", "/HELP please")), worker.HELP_TEXT)

    def test_media_placeholders(self) -> None:
        self.assertIn("voice note", worker.respond(_msg("voice")))
        self.assertIn("photo", worker.respond(_msg("photo")))
        self.assertIn("ch1.pdf", worker.respond(_msg("document", file_name="ch1.pdf")))

    def test_empty_text(self) -> None:
        self.assertEqual(worker.respond(_msg("text", "   ")), "You said:    ")


@mock.patch.dict(sys.modules, {"botocore": _fake_botocore, "botocore.exceptions": _fake_exceptions})
@mock.patch.dict(os.environ, {"DEDUP_TABLE": "dedup"})
class DeduplicationTest(unittest.TestCase):
    def test_first_time(self) -> None:
        dynamo = mock.Mock()
        with mock.patch.object(worker, "_dynamodb", return_value=dynamo):
            self.assertTrue(worker.first_time_seen(5))
        kwargs = dynamo.put_item.call_args.kwargs
        self.assertEqual(kwargs["Item"]["update_id"], {"N": "5"})
        self.assertIn("attribute_not_exists", kwargs["ConditionExpression"])

    def test_duplicate(self) -> None:
        dynamo = mock.Mock()
        dynamo.put_item.side_effect = FakeClientError("ConditionalCheckFailedException")
        with mock.patch.object(worker, "_dynamodb", return_value=dynamo):
            self.assertFalse(worker.first_time_seen(5))

    def test_other_errors_propagate(self) -> None:
        dynamo = mock.Mock()
        dynamo.put_item.side_effect = FakeClientError("ProvisionedThroughputExceededException")
        with (
            mock.patch.object(worker, "_dynamodb", return_value=dynamo),
            self.assertRaises(FakeClientError),
        ):
            worker.first_time_seen(5)


def _record(message_id: str, text: str) -> dict:
    update = {
        "update_id": int(message_id),
        "message": {"from": {"id": 42}, "chat": {"id": 42}, "text": text},
    }
    return {"messageId": message_id, "body": json.dumps(update)}


class HandlerTest(unittest.TestCase):
    def test_replies_and_reports_partial_failures(self) -> None:
        telegram = mock.Mock()
        telegram.send_message.side_effect = [None, RuntimeError("Telegram down")]
        with (
            mock.patch.object(worker, "_telegram", return_value=telegram),
            mock.patch.object(worker, "first_time_seen", return_value=True),
        ):
            result = worker.handler({"Records": [_record("1", "a"), _record("2", "b")]}, None)
        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "2"}]})
        telegram.send_message.assert_any_call(42, "You said: a")

    def test_skips_duplicates(self) -> None:
        telegram = mock.Mock()
        with (
            mock.patch.object(worker, "_telegram", return_value=telegram),
            mock.patch.object(worker, "first_time_seen", return_value=False),
        ):
            result = worker.handler({"Records": [_record("1", "a")]}, None)
        self.assertEqual(result, {"batchItemFailures": []})
        telegram.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
