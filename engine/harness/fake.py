"""A deterministic scripted harness.

The orchestrator, oracle plumbing, ledger, scoring and run record all need to
be tested without paying for a model or waiting on a network. This harness
mutates the workspace exactly as told, so a test can say "this stage fails
twice then passes" and get that, every time.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable

from .base import HarnessAdapter, HarnessRequest, HarnessResult

# A behavior is either a callable(request) or a list of actions:
#   {"write": {rel: text}} | {"remove": [rel]} | {"shell": "cmd"} | {"noop": true}
Behavior = Callable[[HarnessRequest], None] | list[dict] | str


class FakeHarness(HarnessAdapter):
    name = "fake"

    def __init__(self, script: dict[str, Behavior] | None = None,
                 model: str = "fake-model", default: Behavior = "noop"):
        super().__init__(model=model)
        self.script = dict(script or {})
        self.default = default
        self.calls: list[HarnessRequest] = []

    def available(self) -> tuple[bool, str]:
        return True, ""

    def label(self) -> str:
        return self.model or "fake-model"

    def run(self, request: HarnessRequest) -> HarnessResult:
        self.calls.append(request)
        started = time.monotonic()
        behavior = self.script.get(request.stage_id, self.default)
        if callable(behavior):
            behavior(request)
            actions = [{"call": True}]
        elif isinstance(behavior, str):
            actions = [{"noop": True}]
        else:
            actions = behavior

        tool_calls = 0
        for action in actions:
            if action.get("noop"):
                continue
            tool_calls += 1
            if "write" in action:
                for rel, content in action["write"].items():
                    target = request.workspace / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
            if "remove" in action:
                for rel in action["remove"]:
                    victim = request.workspace / rel
                    if victim.is_dir():
                        import shutil
                        shutil.rmtree(victim, ignore_errors=True)
                    elif victim.exists():
                        victim.unlink()
            if "shell" in action:
                subprocess.run(action["shell"], shell=True, cwd=str(request.workspace),
                               capture_output=True, text=True)
        return HarnessResult(exit_code=0, tool_calls=tool_calls,
                             seconds=round(time.monotonic() - started, 3),
                             tokens=100 * max(1, tool_calls),
                             events=[{"type": "tool.call", "tool": "fake"}] * tool_calls,
                             text="fake harness")
