"""Stage and board definitions.

A stage is a directory: stage.yaml plus workspace/ plus oracle/. The YAML is
validated aggressively here so a malformed stage fails at load time with a
readable message rather than as a confusing oracle error mid-run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    # The engine's only third-party dependency. Fail with an instruction rather
    # than a traceback, because the person hitting this has just cloned the repo.
    raise ModuleNotFoundError(
        "PyYAML is required to read stage and board definitions. "
        "Install the pinned dependencies: pip install -r requirements.txt"
    ) from exc

# Oracle kinds the engine knows how to execute. Adding one means adding a
# class in oracles.py and listing it here.
ORACLE_KINDS = {
    "file_exact",
    "file_normalized",
    "json_equal",
    "diff_budget",
    "command",
    "script",
    "mutation",
    "timing",
}

REVEAL_LEVELS = ("minimal", "standard", "full")

DEFAULT_ATTEMPTS = 3
DEFAULT_TIMEOUT_S = 240
DEFAULT_TOOL_BUDGET = 40


class SpecError(Exception):
    """A stage or board file is malformed or refers to missing files."""


@dataclass
class OracleSpec:
    kind: str
    reveal: str = "minimal"
    config: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict, where: str) -> "OracleSpec":
        if not isinstance(raw, dict):
            raise SpecError(f"{where}: oracle must be a mapping, got {type(raw).__name__}")
        kind = raw.get("kind")
        if kind not in ORACLE_KINDS:
            raise SpecError(f"{where}: unknown oracle kind {kind!r}; known: {sorted(ORACLE_KINDS)}")
        reveal = raw.get("reveal", "minimal")
        if reveal not in REVEAL_LEVELS:
            raise SpecError(f"{where}: reveal must be one of {REVEAL_LEVELS}, got {reveal!r}")
        config = {k: v for k, v in raw.items() if k not in ("kind", "reveal")}
        return cls(kind=kind, reveal=reveal, config=config)


@dataclass
class Stage:
    id: str
    name: str
    tier: int
    region: str
    brief: str
    path: Path
    capabilities: list[str] = field(default_factory=list)
    attempts: int = DEFAULT_ATTEMPTS
    timeout_s: int = DEFAULT_TIMEOUT_S
    tool_budget: int = DEFAULT_TOOL_BUDGET
    network: str = "none"
    protected: list[str] = field(default_factory=list)
    oracles: list[OracleSpec] = field(default_factory=list)
    score_base: int = 100
    seedable: bool = False
    setup: str | None = None

    @property
    def workspace(self) -> Path:
        return self.path / "workspace"

    @property
    def oracle_dir(self) -> Path:
        return self.path / "oracle"

    def value(self) -> int:
        """Stage value rises with tier: 100 * (1 + 0.5 * (tier - 1))."""
        return int(self.score_base * (1 + 0.5 * (self.tier - 1)))


def _require(raw: dict, key: str, where: str) -> Any:
    if key not in raw or raw[key] in (None, ""):
        raise SpecError(f"{where}: missing required key {key!r}")
    return raw[key]


def load_stage(path: Path) -> Stage:
    """Load stages/<id>/stage.yaml and check that everything it points at exists."""
    # Absolute on purpose: oracles run with a different cwd, so a relative stage
    # path would resolve against the sandbox and miss the checker entirely.
    path = Path(path).resolve()
    where = str(path)
    if not path.exists():
        raise SpecError(f"{where}: not found")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SpecError(f"{where}: top level must be a mapping")

    stage_id = _require(raw, "id", where)
    brief = raw.get("brief")
    if not brief and raw.get("brief_file"):
        brief_path = path.parent / raw["brief_file"]
        if not brief_path.exists():
            raise SpecError(f"{where}: brief_file {raw['brief_file']!r} does not exist")
        brief = brief_path.read_text(encoding="utf-8")
    if not brief:
        raise SpecError(f"{where}: need either brief or brief_file")

    tier = int(raw.get("tier", 1))
    if not 1 <= tier <= 6:
        raise SpecError(f"{where}: tier must be 1..6, got {tier}")

    oracles = [OracleSpec.from_dict(o, where) for o in raw.get("oracles", [])]
    if not oracles:
        raise SpecError(f"{where}: a stage with no oracles cannot be verified")

    stage = Stage(
        id=stage_id,
        name=raw.get("name", stage_id),
        tier=tier,
        region=raw.get("region", "unassigned"),
        capabilities=list(raw.get("capabilities", [])),
        brief=str(brief).strip(),
        path=path.parent,
        attempts=int(raw.get("attempts", DEFAULT_ATTEMPTS)),
        timeout_s=int(raw.get("timeout_s", DEFAULT_TIMEOUT_S)),
        tool_budget=int(raw.get("tool_budget", DEFAULT_TOOL_BUDGET)),
        network=raw.get("network", "none"),
        protected=list(raw.get("protected", [])),
        oracles=oracles,
        score_base=int(raw.get("score", {}).get("base", 100)),
        seedable=bool(raw.get("seedable", False)),
        setup=raw.get("setup"),
    )

    if not stage.workspace.is_dir():
        raise SpecError(f"{where}: workspace/ directory is required")
    for spec in stage.oracles:
        _validate_oracle_files(stage, spec, where)
    return stage


def _validate_oracle_files(stage: Stage, spec: OracleSpec, where: str) -> None:
    """Fail early when an oracle references a file that is not there."""
    expect = spec.config.get("expect")
    if expect and not (stage.oracle_dir / expect).exists():
        raise SpecError(f"{where}: oracle expect {expect!r} not found under oracle/")
    entry = spec.config.get("entry")
    if entry and not (stage.oracle_dir / entry).exists():
        raise SpecError(f"{where}: oracle entry {entry!r} not found under oracle/")
    if spec.kind == "mutation":
        target = spec.config.get("target")
        if not target:
            raise SpecError(f"{where}: mutation oracle needs a target file")
        if not spec.config.get("mutants"):
            raise SpecError(f"{where}: mutation oracle needs a mutants list")
        if not spec.config.get("test_command"):
            raise SpecError(f"{where}: mutation oracle needs test_command")


@dataclass
class Board:
    id: str
    version: str
    stages: list[Stage]
    path: Path | None = None

    @property
    def size(self) -> int:
        return len(self.stages)


def load_board(path: Path) -> Board:
    """Load a board file: an ordered list of stage directories."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    stages_dir = path.parent.parent / "stages"
    entries = raw.get("stages")
    if not entries:
        raise SpecError(f"{path}: no stages listed")

    stages: list[Stage] = []
    for entry in entries:
        stage_path = stages_dir / entry / "stage.yaml"
        if not stage_path.exists():
            raise SpecError(f"{path}: stage {entry!r} not found at {stage_path}")
        stages.append(load_stage(stage_path))

    ids = [s.id for s in stages]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SpecError(f"{path}: duplicate stage ids {sorted(dupes)}")

    return Board(id=raw.get("id", path.stem), version=str(raw.get("version", "0")),
                 stages=stages, path=path)
