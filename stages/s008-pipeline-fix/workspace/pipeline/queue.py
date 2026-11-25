"""Priority task queue shared by all workers."""

import heapq


class TaskQueue:
    """Bounded-priority queue: `pop()` returns the highest-priority task.

    Higher `priority` wins. Tasks with equal priority come out in the order they
    went in. `join()` blocks until every task handed out has been marked done
    with `task_done()`.
    """

    def __init__(self):
        self._items = []
        self._outstanding = 0
        self._done = 0

    def push(self, task, priority=0):
        self._items.append((priority, task))
        self._outstanding += 1

    def pop(self, block=True, timeout=None):
        if not self._items:
            if not block:
                raise LookupError("queue is empty")
            raise LookupError("queue is empty")
        priority, task = self._items.pop(0)
        self._done += 1
        return task

    def task_done(self):
        self._done += 1

    def join(self):
        while self._done < self._outstanding:
            pass

    def qsize(self):
        return len(self._items)
