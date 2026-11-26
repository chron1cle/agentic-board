"""The game loop.

Three attempts per stage, pristine workspace each time, oracle run by the
engine and never callable by the agent, three failures ends the run. That is
the whole game; everything else here is bookkeeping to make the result
reproducible and auditable.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from . import oracles as oracle_mod
from .feedback import (AttemptRecord, VERDICT_INCOMPLETE, VERDICT_ERROR, VERDICT_FAIL,
                       VERDICT_INTEGRITY, VERDICT_PASS, build_prompt)
from .harness.base import HarnessAdapter, HarnessRequest
from .runrecord import RunRecord, StageResult
from .sandbox import Sandbox
from .scoring import score_stage, segment_scores
from .spec import Board, SpecError, Stage


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
    segment: str | None = None
    world: int | None = None

    def stages(self) -> list[Stage]:
        stages = list(self.board.stages)
        if self.world is not None:
            if self.segment or self.only or self.limit is not None:
                raise SpecError("--world cannot be combined with --segment, --limit, or --only")
            if not 1 <= self.world <= len(self.board.segments):
                raise SpecError(f"unknown world {self.world}; this board has {len(self.board.segments)} worlds")
            segment = self.board.segments[self.world - 1]
            return stages[segment.first - 1:segment.last]
        if self.segment:
            if self.only or self.limit is not None:
                raise SpecError("--segment cannot be combined with --limit or --only")
            for segment in self.board.segments:
                if segment.id == self.segment:
                    return stages[segment.first - 1:segment.last]
            available = ", ".join(segment.id for segment in self.board.segments)
            raise SpecError(f"unknown segment {self.segment!r}; available: {available or 'none'}")
        if self.only:
            picked = [s for s in stages if s.id == self.only or s.id.endswith(self.only)]
            if not picked:
                raise SpecError(f"no stage matches {self.only!r}")
            if len(picked) != 1:
                raise SpecError(f"multiple stages match {self.only!r}")
            stages = picked
        if self.limit is not None:
            if self.limit < 1:
                raise SpecError("--limit must be positive")
            stages = stages[: self.limit]
        return stages


class Orchestrator:
    def __init__(self, config: RunConfig, adapter: HarnessAdapter,
                 on_event=None):
        self.stages = config.stages()
        self.config = config
        self.adapter = adapter
        self.on_event = on_event or (lambda event: None)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.run_id = config.run_id or f"{stamp}-{time.time_ns() % 10**9:09d}"
        if Path(self.run_id).name != self.run_id or self.run_id in {"", ".", ".."}:
            raise SpecError("run ID must be a single directory name")
        # Absolute, always. Oracles run with cwd set to the sandbox workspace, so
        # a relative --out would resolve against the wrong directory and every
        # script oracle would report "checker produced no verdict".
        self.run_dir = (Path(config.out_dir) / self.run_id).resolve()
        try:
            self.run_dir.mkdir(parents=True)
        except FileExistsError as exc:
            raise SpecError(f"run ID {self.run_id!r} already exists") from exc
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
        """Restore a clean checker copy before each attempt."""
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

    def _verify_at_timeout(self, stage: Stage, box: Sandbox) -> list:
        """Grade the stopped attempt once, preserving the workspace as it was submitted."""
        try:
            with tempfile.TemporaryDirectory(prefix="board-deadline-") as tmp:
                snapshot = Sandbox(Path(tmp), box.original, stage.protected)
                shutil.copytree(box.workspace, snapshot.workspace, symlinks=True)
                snapshot.oracle_dir = box.oracle_dir
                snapshot.oracle_seed = box.oracle_seed
                return self._verify(stage, snapshot)
        except OSError:
            return [oracle_mod.Check("snapshot:error", False, "could not copy the deadline workspace")]

    # -- one stage ---------------------------------------------------------
    def play_stage(self, stage: Stage, index: int) -> StageResult:
        result = StageResult(id=stage.id, name=stage.name, tier=stage.tier,
                             region=stage.region)
        self.emit("stage.entered", index=index, stage=stage.id, tier=stage.tier,
                  name=stage.name, **self.config.board.world_level(index))

        attempts: list[AttemptRecord] = []
        # DESIGN.md §5: the wall clock budget is per stage, across all its
        # attempts, not per attempt. Otherwise three failures buy three full
        # budgets and the leaderboard measures patience.
        stage_clock = time.monotonic()
        for number in range(1, stage.attempts + 1):
            attempt_dir = self.run_dir / stage.id / f"attempt{number}"
            box = Sandbox.provision(stage, attempt_dir)
            box.oracle_dir = self._stage_oracle_dir(stage)
            box.oracle_seed = self.config.seed if stage.seedable else None
            fingerprint = box.fingerprint()
            if not result.fingerprint:
                result.fingerprint = fingerprint
            elif fingerprint != result.fingerprint:
                # Every attempt at a stage must start from the same fixture.
                self.emit("stage.void", stage=stage.id, reason="provisioning drift")
                result.status = VERDICT_ERROR
                result.attempts = attempts
                return result

            left = stage.timeout_s - (time.monotonic() - stage_clock)
            if left < 1:
                self.emit("attempt.ended", stage=stage.id, attempt=number,
                          verdict=VERDICT_INCOMPLETE, started=False, timed_out=True, tools=0, seconds=0, tokens=0,
                          failed=["stage-clock"])
                attempts.append(AttemptRecord(
                    n=number, verdict=VERDICT_INCOMPLETE, started=False, timed_out=True,
                    checks=[oracle_mod.Check("stage-clock", False,
                                             f"stage budget of {stage.timeout_s}s "
                                             "exhausted before this attempt",
                                             reveal="full")]))
                result.status = VERDICT_INCOMPLETE
                break

            prompt = build_prompt(stage.brief, attempts, stage.attempts - number,
                                  stage.tool_budget, int(left))
            self.emit("attempt.started", stage=stage.id, attempt=number)
            harness_result = self.adapter.run(HarnessRequest(
                prompt=prompt, workspace=box.workspace, timeout_s=int(left),
                stage_id=stage.id, attempt=number, model=self.config.model))
            violations = box.integrity_violations()
            if violations:
                verdict = VERDICT_INTEGRITY
                checks = [oracle_mod.Check("integrity", False,
                                           "protected paths modified: "
                                           + ", ".join(violations[:6]), reveal="full")]
            elif not harness_result.ok and not harness_result.timed_out:
                verdict = VERDICT_ERROR
                checks = [oracle_mod.Check("harness-error", False, "harness reported an error")]
            else:
                checks = (self._verify_at_timeout(stage, box) if harness_result.timed_out
                          else self._verify(stage, box))
                if not checks or any(c.name.endswith((":error", ":timeout")) for c in checks):
                    verdict = VERDICT_ERROR
                elif all(c.ok for c in checks):
                    verdict = VERDICT_PASS
                elif harness_result.timed_out:
                    verdict = VERDICT_INCOMPLETE
                else:
                    verdict = VERDICT_FAIL

            self._write_transcript(stage, number, prompt, harness_result)
            record = AttemptRecord(
                n=number, verdict=verdict, checks=checks,
                tool_calls=harness_result.tool_calls,
                seconds=round(harness_result.seconds, 2),
                tokens=harness_result.tokens,
                tools_reported=harness_result.tools_reported,
                tokens_reported=harness_result.tokens_reported, timed_out=harness_result.timed_out)
            attempts.append(record)
            result.attempts_used = number
            result.tool_calls += harness_result.tool_calls
            result.seconds += record.seconds
            result.tokens += harness_result.tokens
            if verdict == VERDICT_INTEGRITY:
                result.integrity_violation = True

            self.emit("attempt.ended", stage=stage.id, attempt=number,
                      verdict=verdict, timed_out=record.timed_out, tools=harness_result.tool_calls,
                      seconds=record.seconds, tokens=harness_result.tokens,
                      failed=[c.name for c in checks if not c.ok])

            if verdict in (VERDICT_INTEGRITY, VERDICT_ERROR, VERDICT_INCOMPLETE):
                result.status = verdict
                break

            if verdict == VERDICT_PASS:
                result.cleared = True
                result.points = score_stage(
                    stage.tier, number, tools_used=result.tool_calls,
                    tool_budget=stage.tool_budget * number,
                    seconds=result.seconds, base=stage.score_base)
                self.emit("stage.cleared", stage=stage.id, attempt=number,
                          points=result.points)
                break

        if result.status == VERDICT_INCOMPLETE:
            self.emit("stage.incomplete", stage=stage.id, attempts=result.attempts_used)
        elif not result.cleared:
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
            "timed_out": harness_result.timed_out,
            "tool_calls": harness_result.tool_calls,
            "tokens": harness_result.tokens,
            "seconds": harness_result.seconds,
            "error": harness_result.error,
            "text": harness_result.text,
            "events": harness_result.events,
        }, indent=2), encoding="utf-8")

    # -- the run -----------------------------------------------------------
    def run(self) -> RunRecord:
        stages = self.stages
        status = "benchmark"
        if self.config.harness in {"fake", "solve"}:
            status = "control"
        elif self.config.only or len(stages) != self.config.board.size:
            status = "partial"
        selected_ids = [stage.id for stage in stages]
        first_stage = self.config.board.stages.index(stages[0]) + 1
        partial = len(stages) != self.config.board.size
        selection = f"{first_stage}-{first_stage + len(stages) - 1}" if partial else None
        record = RunRecord(
            run=self.run_id, harness=self.config.harness,
            model=self.config.model or getattr(self.adapter, "label", lambda: None)(),
            board=self.config.board.id, board_version=self.config.board.version,
            seed=self.config.seed, board_size=self.config.board.size,
            selected_stages=len(stages), status=status, selection=selection, first_stage=first_stage,
            world_levels={i: self.config.board.world_level(i)
                          for i in range(first_stage, first_stage + len(stages))})
        self.emit("run.started", harness=record.harness, model=record.model,
                  board=record.board, stages=len(stages))

        for index, stage in enumerate(stages, start=1):
            position = first_stage + index - 1
            stage_result = self.play_stage(stage, position)
            record.stages.append(stage_result)
            if stage_result.status:
                record.status = stage_result.status
            elif record.status == "benchmark" and any(not attempt.tools_reported for attempt in stage_result.attempts):
                record.status = "telemetry_incomplete"
            if not stage_result.cleared:
                # Three failures ends the run. The highest stage cleared is
                # the level achieved; there is no playing past a locked door.
                if index < len(stages):
                    record.notes.append(
                        f"run ended at stage {position} ({stage.id}); "
                        f"{len(stages) - index} stage(s) not played")
                break

        if any(not attempt.tools_reported or not attempt.tokens_reported
               for stage in record.stages for attempt in stage.attempts):
            record.notes.append("One or more attempts omitted tool or token accounting.")
        record.score_segments = segment_scores(self.config.board, selected_ids, record.cumulative_score())
        record.finished = time.time()
        self.emit("run.ended", status=record.status, stageReached=record.stage_reached,
                  points=record.points, stoppedAt=record.stopped_at, selectedStages=len(stages))
        record.save(self.run_dir)
        return record
