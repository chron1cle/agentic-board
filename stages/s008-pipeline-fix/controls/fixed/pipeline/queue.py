"""Priority task queue shared by all workers."""

import heapq
import threading


class TaskQueue:
    """Bounded-priority queue: `pop()` returns the highest-priority task."""

    def __init__(self):
        self._items = []
        self._seq = 0
        self._outstanding = 0
        self._cond = threading.Condition()

    def push(self, task, priority=0):
        with self._cond:
            self._seq += 1
            heapq.heappush(self._items, (-priority, self._seq, task))
            self._outstanding += 1
            self._cond.notify()

    def pop(self, block=True, timeout=None):
        with self._cond:
            while not self._items:
                if not block:
                    raise LookupError("queue is empty")
                if not self._cond.wait(timeout):
                    raise LookupError("queue is empty")
            return heapq.heappop(self._items)[2]

    def task_done(self):
        with self._cond:
            if self._outstanding > 0:
                self._outstanding -= 1
            self._cond.notify_all()

    def join(self):
        with self._cond:
            while self._outstanding > 0:
                self._cond.wait(0.05)

    def qsize(self):
        with self._cond:
            return len(self._items)
