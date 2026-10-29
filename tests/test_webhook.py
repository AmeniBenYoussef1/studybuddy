import json
import os
import unittest
from unittest import mock

from webhook import handler as webhook

SECRET = "test-secret"


def _event(body: dict, secret: str = SECRET) -> dict:
    return {
        "headers": {"x-telegram-bot-api-secret-token": secret},
        "body": json.dumps(body),
    }


def _text_update(user_id: int) -> dict:
    return {
        "update_id": 7,
        "message": {
            "from": {"id": user_id, "first_name": "A"},
            "chat": {"id": user_id},
            "text": "hi",
        },
    }


@mock.patch.dict(os.environ, {"ALLOWED_USER_IDS": "42, 43", "QUEUE_URL": "https://queue"})
@mock.patch.object(webhook, "telegram_secrets", return_value={"webhook_secret": SECRET})
class WebhookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sqs = mock.Mock()
        patcher = mock.patch.object(webhook, "_sqs", return_value=self.sqs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_rejects_wrong_secret(self, _secrets: mock.Mock) -> None:
        response = webhook.handler(_event(_text_update(42), secret="wrong"), None)
        self.assertEqual(response["statusCode"], 401)
        self.sqs.send_message.assert_not_called()

    def test_rejects_missing_secret(self, _secrets: mock.Mock) -> None:
        response = webhook.handler({"headers": {}, "body": "{}"}, None)
        self.assertEqual(response["statusCode"], 401)

    def test_queues_allowed_user(self, _secrets: mock.Mock) -> None:
        response = webhook.handler(_event(_text_update(42)), None)
        self.assertEqual(response["statusCode"], 200)
        self.sqs.send_message.assert_called_once()
        sent = json.loads(self.sqs.send_message.call_args.kwargs["MessageBody"])
        self.assertEqual(sent["update_id"], 7)

    def test_drops_unknown_user_but_returns_200(self, _secrets: mock.Mock) -> None:
        response = webhook.handler(_event(_text_update(999)), None)
        self.assertEqual(response["statusCode"], 200)
        self.sqs.send_message.assert_not_called()

    def test_ignores_unsupported_update(self, _secrets: mock.Mock) -> None:
        response = webhook.handler(_event({"update_id": 1, "edited_message": {}}), None)
        self.assertEqual(response["statusCode"], 200)
        self.sqs.send_message.assert_not_called()

    def test_bad_json(self, _secrets: mock.Mock) -> None:
        event = {"headers": {"x-telegram-bot-api-secret-token": SECRET}, "body": "{not json"}
        self.assertEqual(webhook.handler(event, None)["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
