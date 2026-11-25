"""Tests for the app layer. These are written against the v1 bus."""

import unittest

import app.notifier as notifier
from app.ingest import ingest
from app.retry import with_retry


class FakeBus:
    def __init__(self, *args, **kwargs):
        self.sent = []
        self._closed = False

    def send(self, kind, payload):
        if self._closed:
            return False
        self.sent.append((kind, payload))
        return True

    def close(self):
        self._closed = True


class NotifierTest(unittest.TestCase):
    def setUp(self):
        self._saved = notifier._bus
        notifier._bus = FakeBus()

    def tearDown(self):
        notifier._bus = self._saved

    def test_notify_sends(self):
        self.assertTrue(notifier.notify("u1", "hello"))
        self.assertEqual(notifier._bus.sent,
                         [("user.notify", {"user": "u1", "text": "hello"})])


class RetryTest(unittest.TestCase):
    def test_gives_up_quietly(self):
        self.assertFalse(with_retry(lambda: False, attempts=2))

    def test_stops_at_first_success(self):
        calls = []

        def fn():
            calls.append(1)
            return len(calls) == 2

        self.assertTrue(with_retry(fn, attempts=5))
        self.assertEqual(len(calls), 2)


class IngestTest(unittest.TestCase):
    def test_counts_taken(self):
        import app.ingest as ingest_mod
        saved = ingest_mod.Bus
        ingest_mod.Bus = FakeBus
        try:
            self.assertEqual(ingest([{"a": 1}, {"a": 2}]), 2)
        finally:
            ingest_mod.Bus = saved


if __name__ == "__main__":
    unittest.main()
