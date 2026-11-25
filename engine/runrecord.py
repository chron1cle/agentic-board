"""The run record: one file that is both the score sheet and the replay tape.

The 3D board and the results viewer read this and nothing else, so the renderer
can never disagree with the scoreboard about what happened.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .feedback import AttemptRecord
from .scoring import feedback_counts, feedback_uptake, first_try_rate

SCHEMA_VERSION = 2


@dataclass
class StageResult:
    id: str
    name: str
    tier: int
    region: str = ""
    cleared: bool = False
    attempts_used: int = 0
    points: float = 0.0
    attempts: list[AttemptRecord] = field(default_factory=list)
    fingerprint: str = ""
    integrity_violation: bool = False
    status: str = ""
    tool_calls: int = 0
    seconds: float = 0.0
    tokens: int = 0

    def as_dict(self) -> dict:
        out = asdict(self)
        out["attempts"] = [a.as_dict() for a in self.attempts]
        return out


@dataclass
class RunRecord:
    run: str
    harness: str
    model: str
    board: str
    board_version: str
    seed: int
    started: float = field(default_factory=time.time)
    finished: float | None = None
    stages: list[StageResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    schema: int = SCHEMA_VERSION
    board_size: int | None = None
    selected_stages: int | None = None
    status: str = "benchmark"
    selection: str | None = None
    first_stage: int = 1
    score_segments: list[dict] = field(default_factory=list)
    world_levels: dict[int, dict[str, int]] = field(default_factory=dict)

    # -- derived metrics ---------------------------------------------------
    @property
    def points(self) -> float:
        return round(sum(s.points for s in self.stages), 2)

    @property
    def stage_reached(self) -> int:
        """Highest stage index cleared. This is the headline level."""
        return sum(1 for s in self.stages if s.cleared)

    @property
    def stopped_at(self) -> str:
        for stage in self.stages:
            if not stage.cleared:
                return stage.id
        if self.board_size is not None and self.stage_reached < self.board_size:
            return "selection_complete"
        return "complete"

    @property
    def first_try_rate(self) -> float:
        return first_try_rate(self.stages)

    @property
    def feedback_uptake(self) -> float:
        return feedback_uptake(self.stages)

    @property
    def totals(self) -> dict:
        return {
            "tool_calls": sum(s.tool_calls for s in self.stages),
            "seconds": round(sum(s.seconds for s in self.stages), 2),
            "tokens": sum(s.tokens for s in self.stages),
            "attempts": sum(a.started for s in self.stages for a in s.attempts),
        }

    def cumulative_score(self) -> list[dict]:
        """Score after each stage. This is what the replay button animates."""
        running = 0.0
        out = []
        for index, stage in enumerate(self.stages, start=self.first_stage):
            running = round(running + stage.points, 2)
            out.append({
                "index": index,
                **self.world_levels.get(index, {}),
                "stage": stage.id,
                "name": stage.name,
                "tier": stage.tier,
                "region": stage.region,
                "cleared": stage.cleared,
                "attempts": stage.attempts_used,
                "points": stage.points,
                "cumulative": running,
                "seconds": stage.seconds,
                "tool_calls": stage.tool_calls,
                # the three attempt crystals on the board
                "attemptResults": [a.verdict for a in stage.attempts],
            })
        return out

    # -- serialization -----------------------------------------------------
    def as_dict(self) -> dict:
        return {
            "schema": self.schema,
            "run": self.run,
            "harness": self.harness,
            "model": self.model,
            "board": self.board,
            "board_version": self.board_version,
            "seed": self.seed,
            "status": self.status,
            "selection": self.selection,
            "scoreSegments": self.score_segments,
            "started": self.started,
            "finished": self.finished,
            "notes": self.notes,
            "stages": [s.as_dict() for s in self.stages],
            "final": {
                "stageReached": self.stage_reached,
                "stoppedAt": self.stopped_at,
                "points": self.points,
                "firstTryRate": self.first_try_rate,
                "feedbackUptake": self.feedback_uptake,
                "feedbackTrials": feedback_counts(self.stages)[1],
                "boardSize": self.board_size if self.board_size is not None else len(self.stages),
                "selectedStages": self.selected_stages,
                **self.totals,
            },
            "timeline": self.cumulative_score(),
        }

    def save(self, root: Path) -> Path:
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        target = root / "run.json"
        target.write_text(json.dumps(self.as_dict(), indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))
