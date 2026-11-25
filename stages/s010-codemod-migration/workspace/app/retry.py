"""Retry helper for bus sends."""

import time


def with_retry(fn, attempts=3, delay=0.0):
    """The v1 bus reports failure by returning False, so that is what we check."""
    for _ in range(attempts):
        if fn():
            return True
        if delay:
            time.sleep(delay)
    return False
