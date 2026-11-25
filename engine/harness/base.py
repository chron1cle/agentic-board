"""Harness adapter interface.

Deliberately narrow: one call, no session resume. Attempts are stateless by
design (DESIGN.md §2), which is what lets any headless one-shot CLI be an
adapter without special support.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HarnessRequest:
    prompt: str
    workspace: Path
    timeout_s: int
    stage_id: str = ""
    attempt: int = 1
    model: str | None = None


@dataclass
class HarnessResult:
    exit_code: int = 0
    tool_calls: int = 0
    seconds: float = 0.0
    tokens: int = 0
    events: list[dict] = field(default_factory=list)
    text: str = ""
    error: str = ""
    raw: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.error


class HarnessAdapter:
    name = "base"

    def __init__(self, model: str | None = None, bin_path: str | None = None):
        self.model = model
        self.bin_path = bin_path

    def run(self, request: HarnessRequest) -> HarnessResult:  # pragma: no cover
        raise NotImplementedError

    def available(self) -> tuple[bool, str]:
        """(is_usable, why_not). Checked before a run so failures are loud early."""
        return True, ""


def elapsed(start: float) -> float:
    return round(time.monotonic() - start, 2)
