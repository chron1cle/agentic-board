#!/usr/bin/env python3
"""Hidden tests for TaskQueue: ordering, blocking, join, and thread safety."""

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": bool(ok), "detail": detail,
                      "evidence": str(evidence)[:900]}))


def main():
    try:
        from pipeline import TaskQueue
    except Exception as exc:
        emit("imports", False, f"pipeline does not import: {exc}")
        return 0
    emit("imports", True)

    q = TaskQueue()
    q.push("low", 1)
    q.push("high", 9)
    q.push("mid", 5)
    try:
        got = [q.pop(block=False) for _ in range(3)]
    except Exception as exc:
        got = f"raised {type(exc).__name__}"
    emit("priority-order", got == ["high", "mid", "low"], f"got {got}")

    q = TaskQueue()
    for letter in "abcd":
        q.push(letter, 5)
    got = [q.pop(block=False) for _ in range(4)]
    emit("fifo-within-priority", got == ["a", "b", "c", "d"], f"got {got}")

    q = TaskQueue()
    outcome = []

    def pusher():
        time.sleep(0.2)
        q.push("late", 1)

    thread = threading.Thread(target=pusher)
    thread.start()
    try:
        outcome.append(q.pop(block=True, timeout=5))
    except Exception as exc:
        outcome.append(f"raised {type(exc).__name__}")
    thread.join()
    emit("blocking-pop-waits", outcome == ["late"], f"got {outcome}")

    q = TaskQueue()
    for i in range(5):
        q.push(i)
    for _ in range(5):
        q.pop(block=False)
        q.task_done()
    finished = []
    waiter = threading.Thread(target=lambda: (q.join(), finished.append(True)), daemon=True)
    waiter.start()
    waiter.join(5)
    emit("join-returns", finished == [True], "join() did not return within 5s")

    q = TaskQueue()
    q.push(1)
    q.push(2)
    q.pop(block=False)
    q.task_done()
    early = []
    waiter = threading.Thread(target=lambda: (q.join(), early.append(True)), daemon=True)
    waiter.start()
    waiter.join(0.6)
    emit("join-waits-for-all", early == [], "join() returned with a task outstanding")

    q = TaskQueue()
    errors = []
    seen = []
    stop = threading.Event()

    def producer(count):
        try:
            for i in range(count):
                q.push((threading.current_thread().name, i), i % 7)
        except Exception as exc:
            errors.append(f"producer: {exc!r}")

    def consumer():
        while not stop.is_set() or q.qsize() > 0:
            try:
                seen.append(q.pop(block=False))
            except Exception:
                time.sleep(0.001)

    producers = [threading.Thread(target=producer, args=(500,), name=f"p{n}") for n in range(8)]
    consumers = [threading.Thread(target=consumer, name=f"c{n}") for n in range(3)]
    for thread in consumers + producers:
        thread.start()
    for thread in producers:
        thread.join(30)
    stop.set()
    for thread in consumers:
        thread.join(30)
    unique = len({(t, i) for t, i in seen})
    emit("no-lost-or-duplicated-tasks",
         len(seen) == 4000 and unique == 4000 and not errors,
         f"{len(seen)} handed out, {unique} unique, expected 4000",
         "; ".join(errors[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
