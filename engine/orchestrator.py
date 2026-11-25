"""The game loop.

Three attempts per stage, pristine workspace each time, oracle run by the
engine and never callable by the agent, three failures ends the run. That is
the whole game; everything else here is bookkeeping to make the result
reproducible and auditable.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import oracles as oracle_mod
from .feedback import (AttemptRecord, VERDICT_BUDGET, VERDICT_FAIL,
                       VERDICT_INTEGRITY, VERDICT_PASS, build_prompt)
from .harness.base import HarnessAdapter, HarnessRequest
from .runrecord import RunRecord, StageResult
from .sandbox import Sandbox
from .scoring import score_stage
from .spec import Board, Stage


@dataclass
class RunConfig:
    board: Board
    harness: str = "opencode"
    model: str | None = None
    seed: int = 1
    out_dir: Path = Path("runs")
    run_id: str | None = None
    limit: int | None = None
    only: str | None = None
    keep_workspace: bool = True

    def stages(self) -> list[Stage]:
        stages = list(self.board.stages)
        if self.only:
            picked = [s for s in stages if s.id == self.only or s.id.endswith(self.only)]
            if not picked:
                raise ValueError(f"no stage matches {self.only!r}")
            stages = picked
        if self.limit:
            stages = stages[: self.limit]
        return stages


class Orchestrator:
    def __init__(self, config: RunConfig, adapter: HarnessAdapter,
                 on_event=None):
        self.config = config
        self.adapter = adapter
        self.on_event = on_event or (lambda event: None)
        self.run_id = config.run_id or time.strftime("%Y%m%d-%H%M%S")
        # Absolute, always. Oracles run with cwd set to the sandbox workspace, so
        # a relative --out would resolve against the wrong directory and every
        # script oracle would report "checker produced no verdict".
        self.run_dir = (Path(config.out_dir) / self.run_id).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._oracle_root = self.run_dir / "_oracle"
        self._oracle_root.mkdir(exist_ok=True)
        self._events_path = self.run_dir / "events.jsonl"

    # -- events ------------------------------------------------------------
    def emit(self, kind: str, **payload) -> None:
        event = {"t": round(time.time(), 3), "event": kind, **payload}
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
        self.on_event(event)

    # -- oracles -----------------------------------------------------------
    def _stage_oracle_dir(self, stage: Stage) -> Path:
        """Stage checkers live outside the attempt tree, copied once per stage."""
        target = self._oracle_root / stage.id
        if target.exists():
            shutil.rmtree(target)
        if stage.oracle_dir.is_dir():
            shutil.copytree(stage.oracle_dir, target)
        return target

    def _verify(self, stage: Stage, box: Sandbox) -> list:
        checks = []
        for spec in stage.oracles:
            oracle = oracle_mod.build(spec)
            try:
                checks += oracle.run(box)
            except Exception as exc:  # a broken oracle must not look like an agent failure
                checks.append(oracle_mod.Check(
                    f"{spec.kind}:error", False,
                    f"oracle error: {type(exc).__name__}: {oracle_mod.sanitize(str(exc), 200)}",
                    reveal="full", tier=spec.kind))
        return checks

    # -- one stage ---------------------------------------------------------
    def play_stage(self, stage: Stage, index: int) -> StageResult:
        result = StageResult(id=stage.id, name=stage.name, tier=stage.tier,
                             region=stage.region)
        oracle_dir = self._stage_oracle_dir(stage)
        self.emit("stage.entered", index=index, stage=stage.id, tier=stage.tier,
                  name=stage.name)

        attempts: list[AttemptRecord] = []
        # DESIGN.md §5: the wall clock budget is per stage, across all its
        # attempts, not per attempt. Otherwise three failures buy three full
        # budgets and the leaderboard measures patience.
        stage_clock = time.monotonic()
        for number in range(1, stage.attempts + 1):
            attempt_dir = self.run_dir / stage.id / f"attempt{number}"
            box = Sandbox.provision(stage, attempt_dir)
            box.oracle_dir = oracle_dir
            fingerprint = box.fingerprint()
            if not result.fingerprint:
                result.fingerprint = fingerprint
            elif fingerprint != result.fingerprint:
                # Provisioning must be byte-identical or the attempts are not
                # independent trials and the statistics are meaningless.
                self.emit("stage.void", stage=stage.id, reason="provisioning drift")
                result.attempts = attempts
                return result

            left = stage.timeout_s - (time.monotonic() - stage_clock)
            if left < 1:
                self.emit("attempt.ended", stage=stage.id, attempt=number,
                          verdict=VERDICT_BUDGET, tools=0, seconds=0, tokens=0,
                          failed=["stage-clock"])
                attempts.append(AttemptRecord(
                    n=number, verdict=VERDICT_BUDGET,
                    checks=[oracle_mod.Check("stage-clock", False,
                                             f"stage budget of {stage.timeout_s}s "
                                             "exhausted before this attempt",
                                             reveal="full")]))
                result.attempts = attempts
                break

            prompt = build_prompt(stage.brief, attempts, stage.attempts - number,
                                  stage.tool_budget, left)
            self.emit("attempt.started", stage=stage.id, attempt=number)
            started = time.monotonic()
            harness_result = self.adapter.run(HarnessRequest(
                prompt=prompt, workspace=box.workspace, timeout_s=int(left),
                stage_id=stage.id, attempt=number, model=self.config.model))
            self._write_transcript(stage, number, prompt, harness_result)

            violations = box.integrity_violations()
            if violations:
                verdict = VERDICT_INTEGRITY
                checks = [oracle_mod.Check("integrity", False,
                                           "protected paths modified: "
                                           + ", ".join(violations[:6]), reveal="full")]
            elif harness_result.timed_out:
                verdict = VERDICT_BUDGET
                checks = [oracle_mod.Check("timeout", False,
                                           f"stage budget of {stage.timeout_s}s exhausted",
                                           reveal="full")]
            else:
                checks = self._verify(stage, box)
                verdict = VERDICT_PASS if all(c.ok for c in checks) else VERDICT_FAIL

            record = AttemptRecord(
                n=number, verdict=verdict, checks=checks,
                tool_calls=harness_result.tool_calls,
                seconds=round(time.monotonic() - started, 2),
                tokens=harness_result.tokens,
                note=harness_result.error[:200])
            attempts.append(record)
            result.attempts_used = number
            result.tool_calls += harness_result.tool_calls
            result.seconds += record.seconds
            result.tokens += harness_result.tokens
            if verdict == VERDICT_INTEGRITY:
                result.integrity_violation = True

            self.emit("attempt.ended", stage=stage.id, attempt=number,
                      verdict=verdict, tools=harness_result.tool_calls,
                      seconds=record.seconds, tokens=harness_result.tokens,
                      failed=[c.name for c in checks if not c.ok])

            if verdict == VERDICT_PASS:
                result.cleared = True
                result.points = score_stage(
                    stage.tier, number, tools_used=result.tool_calls,
                    tool_budget=stage.tool_budget * number,
                    seconds=result.seconds)
                self.emit("stage.cleared", stage=stage.id, attempt=number,
                          points=result.points)
                break

        if not result.cleared:
            self.emit("stage.failed", stage=stage.id, attempts=len(attempts))
        result.attempts = attempts
        return result

    def _write_transcript(self, stage: Stage, number: int, prompt: str,
                          harness_result) -> None:
        path = self.run_dir / stage.id / f"attempt{number}.transcript.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "prompt": prompt,
            "exit_code": harness_result.exit_code,
            "tool_calls": harness_result.tool_calls,
            "tokens": harness_result.tokens,
            "seconds": harness_result.seconds,
            "error": harness_result.error,
            "text": harness_result.text,
            "events": harness_result.events,
        }, indent=2), encoding="utf-8")

    # -- the run -----------------------------------------------------------
    def run(self) -> RunRecord:
        stages = self.config.stages()
        record = RunRecord(
            run=self.run_id, harness=self.config.harness,
            model=getattr(self.adapter, "label", lambda: self.config.model)(),
            board=self.config.board.id, board_version=self.config.board.version,
            seed=self.config.seed)
        self.emit("run.started", harness=record.harness, model=record.model,
                  board=record.board, stages=len(stages))

        for index, stage in enumerate(stages, start=1):
            stage_result = self.play_stage(stage, index)
            record.stages.append(stage_result)
            if not stage_result.cleared:
                # Three failures ends the run. The highest stage cleared is
                # the level achieved; there is no playing past a locked door.
                if index < len(stages):
                    record.notes.append(
                        f"run ended at stage {index} ({stage.id}); "
                        f"{len(stages) - index} stage(s) not played")
                break

        record.finished = time.time()
        self.emit("run.ended", stageReached=record.stage_reached,
                  points=record.points, stoppedAt=record.stopped_at)
        record.save(self.run_dir)
        return record
