import unittest

from shared.telegram import parse_update


def _update(**message_fields: object) -> dict:
    message = {
        "message_id": 1,
        "from": {"id": 42, "first_name": "Ameni"},
        "chat": {"id": 42, "type": "private"},
    }
    message.update(message_fields)
    return {"update_id": 1000, "message": message}


class ParseUpdateTest(unittest.TestCase):
    def test_text(self) -> None:
        msg = parse_update(_update(text="hello"))
        assert msg is not None
        self.assertEqual(msg.kind, "text")
        self.assertEqual(msg.text, "hello")
        self.assertEqual(msg.user_id, 42)
        self.assertEqual(msg.update_id, 1000)

    def test_voice(self) -> None:
        msg = parse_update(_update(voice={"file_id": "v1", "duration": 3}))
        assert msg is not None
        self.assertEqual(msg.kind, "voice")
        self.assertEqual(msg.file_id, "v1")

    def test_photo_uses_largest_size_and_caption(self) -> None:
        photo = [{"file_id": "small"}, {"file_id": "large"}]
        msg = parse_update(_update(photo=photo, caption="exercise 3"))
        assert msg is not None
        self.assertEqual(msg.kind, "photo")
        self.assertEqual(msg.file_id, "large")
        self.assertEqual(msg.text, "exercise 3")

    def test_document(self) -> None:
        msg = parse_update(_update(document={"file_id": "d1", "file_name": "ch1.pdf"}))
        assert msg is not None
        self.assertEqual(msg.kind, "document")
        self.assertEqual(msg.file_name, "ch1.pdf")

    def test_unsupported_message_kind(self) -> None:
        msg = parse_update(_update(sticker={"file_id": "s1"}))
        assert msg is not None
        self.assertEqual(msg.kind, "other")

    def test_ignores_non_message_updates(self) -> None:
        self.assertIsNone(parse_update({"update_id": 1, "edited_message": {}}))
        self.assertIsNone(parse_update({"update_id": 1, "message": {"text": "no sender"}}))


if __name__ == "__main__":
    unittest.main()
