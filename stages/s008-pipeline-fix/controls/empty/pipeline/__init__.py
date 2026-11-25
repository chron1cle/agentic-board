"""A tiny work-distribution library.

Three modules, three bug reports on the board, and a release freeze on Friday.
The public API is fixed: `TaskQueue`, `Worker`, `retry` and `summarise` must keep
their names and signatures.
"""

from .queue import TaskQueue
from .report import summarise
from .worker import Worker, retry

__all__ = ["TaskQueue", "Worker", "retry", "summarise"]
