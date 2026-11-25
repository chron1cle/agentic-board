"""The reference harness: plays a stage by installing that stage's own `fixed` control.

This measures nothing about any agent. It exists so the board can be proven
completable through the real game loop — provisioning, ledger, scoring, run
record — without paying for a model, and so the viewer has a full board to
draw. If `engine run --harness solve` fails to reach the last stage, the board
is broken, not the agent.

It reads the answer key on purpose. No real harness may, and the run record
labels it as what it is.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from .base import HarnessAdapter, HarnessRequest, HarnessResult
from .fake import FakeHarness

STAGES_DIR = Path(__file__).resolve().parents[2] / "stages"


class SolveHarness(FakeHarness):
    name = "solve"

    def __init__(self, model: str | None = None, stages_dir: Path | None = None):
        super().__init__(model=model or "reference-controls")
        self.stages_dir = Path(stages_dir) if stages_dir else STAGES_DIR

    def available(self) -> tuple[bool, str]:
        return True, ""

    def label(self) -> str:
        return self.model or "reference-controls"

    def run(self, request: HarnessRequest) -> HarnessResult:
        self.calls.append(request)
        started = time.monotonic()
        fixed = self.stages_dir / request.stage_id / "controls" / "fixed"
        if not fixed.is_dir():
            return HarnessResult(
                exit_code=1, error=f"no reference control at {fixed}",
                seconds=round(time.monotonic() - started, 3))
        # Replace, do not overlay. A control is a complete answer, and some
        # stages are passed by *deleting* something; overlaying would leave the
        # thing that had to go sitting in the workspace.
        for child in Path(request.workspace).iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        shutil.copytree(fixed, request.workspace, dirs_exist_ok=True)
        files = sum(1 for p in Path(request.workspace).rglob("*") if p.is_file())
        return HarnessResult(
            exit_code=0, tool_calls=files,
            seconds=round(time.monotonic() - started, 3),
            tokens=100 * max(1, files),
            events=[{"type": "tool.call", "tool": "reference-copy"}] * files,
            text="reference control installed")
