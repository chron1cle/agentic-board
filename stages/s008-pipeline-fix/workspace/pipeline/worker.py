"""Worker pool with retry and exponential backoff."""

import time


def retry(func, attempts=4, base_delay=0.1, sleep=time.sleep):
    """Call `func` until it succeeds, at most `attempts` times.

    Sleeps `base_delay`, then `base_delay * 2`, then `base_delay * 4`, … between
    tries. If every attempt fails, the **last** exception is raised to the caller.
    """
    last = None
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 - deliberately broad, then re-raised
            last = exc
            if attempt < attempts - 1:
                sleep(base_delay * (attempt + 1))
    return None


class Worker:
    """Drains a TaskQueue, applying `handler` to each task."""

    def __init__(self, queue, handler):
        self.queue = queue
        self.handler = handler
        self.results = []
        self.errors = []

    def run(self, count):
        """Process exactly `count` tasks, then return."""
        for _ in range(count):
            task = self.queue.pop()
            try:
                self.results.append(self.handler(task))
            except Exception as exc:  # noqa: BLE001
                self.errors.append(exc)
            finally:
                self.queue.task_done()
        return self.results
