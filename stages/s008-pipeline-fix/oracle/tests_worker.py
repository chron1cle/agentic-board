#!/usr/bin/env python3
"""Hidden tests for retry backoff and the worker pool."""

import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": bool(ok), "detail": detail,
                      "evidence": str(evidence)[:900]}))


def main():
    try:
        from pipeline import TaskQueue, Worker, retry
    except Exception as exc:
        emit("imports", False, f"pipeline does not import: {exc}")
        return 0
    emit("imports", True)

    calls = []
    delays = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("boom")
        return "ok"

    got = retry(flaky, attempts=5, base_delay=0.1, sleep=delays.append)
    emit("retry-eventually-succeeds", got == "ok", f"returned {got!r}")
    emit("backoff-doubles", delays == [0.1, 0.2], f"sleeps were {delays}")

    def always():
        raise RuntimeError("always")

    try:
        result = retry(always, attempts=3, base_delay=0.001, sleep=lambda d: None)
        emit("retry-reraises-last-error", False, f"returned {result!r} instead of raising")
    except RuntimeError as exc:
        emit("retry-reraises-last-error", str(exc) == "always", f"raised {exc!r}")

    hits = []

    def once():
        hits.append(1)
        raise KeyError("k")

    try:
        retry(once, attempts=1, base_delay=0.001, sleep=lambda d: None)
        emit("single-attempt", False, "no exception raised")
    except KeyError:
        emit("single-attempt", len(hits) == 1, f"called {len(hits)} time(s)")

    queue = TaskQueue()
    for i in range(6):
        queue.push(i, 0)

    def handler(task):
        if task == 3:
            raise ValueError("bad task")
        return task * 10

    worker = Worker(queue, handler)
    results = worker.run(6)
    emit("worker-collects-results", results == [0, 10, 20, 40, 50], f"results={results}")
    emit("worker-records-errors", len(worker.errors) == 1, f"errors={worker.errors}")

    finished = []
    waiter = threading.Thread(target=lambda: (queue.join(), finished.append(True)), daemon=True)
    waiter.start()
    waiter.join(5)
    emit("worker-releases-join", finished == [True],
         "join() hung after every task was handled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
