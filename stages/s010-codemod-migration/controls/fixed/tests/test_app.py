"""Tests for the app layer, written against the v2 SDK."""

import unittest

from app.billing import charge
from app.ingest import ingest
from app.notifier import notify
from app.retry import with_retry
from messenger.v2 import Client, DeliveryError, Event


class RecordingClient:
    def __init__(self, fails=0):
        self.fails = fails
        self.published = []
        self.closed = False

    def publish(self, event):
        if self.fails > 0:
            self.fails -= 1
            raise DeliveryError("broker down")
        self.published.append(event)

    def close(self):
        self.closed = True


class NotifyTest(unittest.TestCase):
    def test_publishes_expected_event(self):
        client = RecordingClient()
        self.assertTrue(notify("u1", "hello", client=client))
        self.assertEqual(len(client.published), 1)
        event = client.published[0]
        self.assertIsInstance(event, Event)
        self.assertEqual(event.kind, "user.notify")
        self.assertEqual(event.body, {"user": "u1", "text": "hello"})
        self.assertEqual(event.key, "u1")

    def test_does_not_close_caller_owned_client(self):
        client = RecordingClient()
        notify("u1", "hi", client=client)
        self.assertFalse(client.closed)

    def test_error_propagates(self):
        with self.assertRaises(DeliveryError):
            notify("u1", "hi", client=RecordingClient(fails=5))


class ChargeTest(unittest.TestCase):
    def test_retries_until_it_lands(self):
        client = RecordingClient(fails=2)
        self.assertTrue(charge("u7", 999, client=client))
        self.assertEqual(len(client.published), 1)
        self.assertEqual(client.published[0].kind, "billing.charge")
        self.assertEqual(client.published[0].key, "u7")

    def test_gives_up_after_three_attempts(self):
        client = RecordingClient(fails=99)
        with self.assertRaises(DeliveryError):
            charge("u7", 999, client=client)
        self.assertEqual(client.fails, 96)


class IngestTest(unittest.TestCase):
    def test_publishes_every_record(self):
        client = RecordingClient()
        self.assertEqual(ingest([{"a": 1}, {"a": 2}], client=client), 2)
        self.assertEqual([e.body for e in client.published], [{"a": 1}, {"a": 2}])
        self.assertTrue(all(e.kind == "ingest.record" for e in client.published))

    def test_error_propagates(self):
        with self.assertRaises(DeliveryError):
            ingest([{"a": 1}], client=RecordingClient(fails=1))


class RetryTest(unittest.TestCase):
    def test_returns_value(self):
        self.assertEqual(with_retry(lambda: "ok"), "ok")

    def test_reraises_after_attempts(self):
        calls = []

        def bad():
            calls.append(1)
            raise DeliveryError("no")

        with self.assertRaises(DeliveryError):
            with_retry(bad, attempts=3)
        self.assertEqual(len(calls), 3)


class ClientTest(unittest.TestCase):
    def test_reads_config(self):
        client = Client()
        self.assertEqual(client.config["broker_host"], "10.0.0.4")
        self.assertEqual(client.config["timeout_ms"], 2500)

    def test_closed_client_refuses(self):
        client = Client()
        client.close()
        with self.assertRaises(DeliveryError):
            client.publish(Event("t", {}))


if __name__ == "__main__":
    unittest.main()
