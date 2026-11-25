"""Retry helper for v2 publishes, where failure is an exception."""

import time

from messenger.v2 import DeliveryError


def with_retry(fn, attempts=3, delay=0.0):
    last = None
    for attempt in range(attempts):
        try:
            return fn()
        except DeliveryError as exc:
            last = exc
            if delay and attempt < attempts - 1:
                time.sleep(delay)
    raise last
