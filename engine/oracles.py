"""Oracles: the checks that decide whether a stage is cleared.

Tiering from DESIGN.md §3. Every check carries a reveal level because the
feedback ledger is the only channel between attempts, and for exact-match
stages the diff *is* the answer — showing it makes attempt 2 free.

Oracle output is untrusted. It contains stderr from code the agent wrote, so
an agent can otherwise smuggle text into attempt 2's prompt through its own
program. Everything here is sanitized before it can reach the ledger.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from .sandbox import Sandbox, normalize_text

MAX_DETAIL = 600
MAX_EVIDENCE = 2000
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str, limit: int = MAX_DETAIL) -> str:
    """Strip control characters and hard-truncate. Untrusted input only."""
    if text is None:
        return ""
    return _CONTROL.sub("", str(text))[:limit]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""        # safe to reveal at reveal=minimal
    evidence: str = ""      # revealed only at reveal=full
    reveal: str = "minimal"
    tier: str = ""

    def as_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail,
                "evidence": self.evidence, "reveal": self.reveal, "tier": self.tier}


@dataclass
class OracleResult:
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(c.ok for c in self.checks)

    def as_dict(self) -> list[dict]:
        return [c.as_dict() for c in self.checks]


class Oracle:
    kind = "base"

    def __init__(self, config: dict, reveal: str = "minimal"):
        self.config = config
        self.reveal = reveal

    def run(self, box: Sandbox) -> list[Check]:  # pragma: no cover - interface
        raise NotImplementedError

    def _expect(self, box: Sandbox) -> Path:
        # Resolved: the sandbox's cwd is the agent's workspace, and a relative
        # oracle dir would otherwise point inside it.
        return Path(box.oracle_dir).resolve() / self.config["expect"]


# --- tier A / B: content equality ------------------------------------------

class FileExact(Oracle):
    """Tier A. Byte equality. Deliberate, and only sound for tiny artifacts."""
    kind = "file_exact"

    def run(self, box: Sandbox) -> list[Check]:
        rel = self.config["path"]
        want = self._expect(box).read_bytes()
        got_path = box.workspace / rel
        if not got_path.exists():
            return [Check(rel, False, "file is missing", reveal=self.reveal, tier="A")]
        got = got_path.read_bytes()
        same = got == want
        detail = "bytes match" if same else (
            f"differs: {len(got)} bytes produced vs {len(want)} expected")
        return [Check(rel, same, detail,
                      evidence="" if same else _byte_evidence(got, want),
                      reveal=self.reveal, tier="A")]


class FileNormalized(Oracle):
    """Tier B. Equality after declared normalization only."""
    kind = "file_normalized"

    def run(self, box: Sandbox) -> list[Check]:
        rel = self.config["path"]
        ops = self.config.get("normalize", [])
        want = normalize_text(self._expect(box).read_text(encoding="utf-8"), ops)
        raw = box.read(rel)
        if raw is None:
            return [Check(rel, False, "file is missing", reveal=self.reveal, tier="B")]
        got = normalize_text(raw, ops)
        if got == want:
            return [Check(rel, True, "matches after normalization",
                          reveal=self.reveal, tier="B")]
        lines_want = want.splitlines()
        lines_got = got.splitlines()
        offsets = [i + 1 for i, (a, b) in enumerate(zip(lines_got, lines_want)) if a != b]
        offsets += range(len(lines_got) + 1, len(lines_want) + 1)
        offsets += range(len(lines_want) + 1, len(lines_got) + 1)
        shown = ", ".join(str(o) for o in offsets[:12])
        detail = (f"{len(offsets)} line(s) differ"
                  + (f" (at line {shown})" if shown else ""))
        return [Check(rel, False, detail,
                      evidence=_line_diff(lines_got, lines_want),
                      reveal=self.reveal, tier="B")]


class JsonEqual(Oracle):
    """Structural equality for JSON, ignoring key order and formatting."""
    kind = "json_equal"

    def run(self, box: Sandbox) -> list[Check]:
        rel = self.config["path"]
        want = json.loads(self._expect(box).read_text(encoding="utf-8"))
        raw = box.read(rel)
        if raw is None:
            return [Check(rel, False, "file is missing", reveal=self.reveal, tier="B")]
        try:
            got = json.loads(raw)
        except json.JSONDecodeError as exc:
            return [Check(rel, False, f"not valid JSON: {sanitize(str(exc), 120)}",
                          reveal=self.reveal, tier="B")]
        paths = _json_diff_paths(got, want)
        if not paths:
            return [Check(rel, True, "structure matches", reveal=self.reveal, tier="B")]
        return [Check(rel, False,
                      f"{len(paths)} field(s) differ: " + ", ".join(paths[:8]),
                      evidence=f"expected {json.dumps(want)[:MAX_EVIDENCE]}",
                      reveal=self.reveal, tier="B")]


# --- tier C: shape of the change -------------------------------------------

class DiffBudget(Oracle):
    """Tier C. Caps how much the agent was allowed to touch."""
    kind = "diff_budget"

    def run(self, box: Sandbox) -> list[Check]:
        limit = int(self.config["max_changed_lines"])
        delta = box.delta()
        if delta.changed_lines <= limit:
            return [Check("diff-budget", True,
                          f"{delta.changed_lines} line(s) changed, limit {limit}",
                          reveal=self.reveal, tier="C")]
        return [Check("diff-budget", False,
                      f"{delta.changed_lines} lines changed, limit {limit}",
                      evidence="touched: " + ", ".join(delta.touched[:20]),
                      reveal=self.reveal, tier="C")]


# --- execution-backed checks -----------------------------------------------

class Command(Oracle):
    """Run a command in the workspace and check exit code and/or stdout."""
    kind = "command"

    def run(self, box: Sandbox) -> list[Check]:
        cmd = self.config["cmd"]
        res = box.run(cmd, timeout=int(self.config.get("timeout_s", 120)))
        name = self.config.get("name", cmd)
        problems = []
        if res.timed_out:
            problems.append("timed out")
        want_exit = int(self.config.get("expect_exit", 0))
        if res.exit_code != want_exit:
            problems.append(f"exit {res.exit_code}, expected {want_exit}")
        if "expect_stdout" in self.config:
            ops = self.config.get("normalize", [])
            got = normalize_text(res.stdout, ops).strip()
            want = normalize_text(str(self.config["expect_stdout"]), ops).strip()
            if got != want:
                problems.append("stdout differs")
                return [Check(name, False, "; ".join(problems),
                              evidence=f"got:\n{sanitize(res.stdout, MAX_EVIDENCE)}",
                              reveal=self.reveal, tier="A")]
        if problems:
            return [Check(name, False, "; ".join(problems),
                          evidence=sanitize(res.stderr or res.stdout, MAX_EVIDENCE),
                          reveal=self.reveal, tier="A")]
        return [Check(name, True, "command succeeded",
                      evidence=sanitize(res.stdout, MAX_EVIDENCE),
                      reveal=self.reveal, tier="A")]


class Timing(Oracle):
    """A performance bound: the command must pass and stay under a limit."""
    kind = "timing"

    def run(self, box: Sandbox) -> list[Check]:
        limit = float(self.config["max_seconds"])
        # Hard-kill a little past the bound: a run that would have finished in
        # 40s against a 10s budget has already failed, and waiting for it is
        # just a slower way to say no.
        res = box.run(self.config["cmd"], timeout=int(limit * 3) + 30)
        name = self.config.get("name", "timing")
        if res.timed_out or res.seconds > limit:
            return [Check(name, False,
                          f"took {res.seconds:.2f}s, exceeded {limit:g}s budget",
                          reveal=self.reveal, tier="D")]
        if res.exit_code != 0:
            return [Check(name, False, f"command failed (exit {res.exit_code})",
                          evidence=sanitize(res.stderr or res.stdout, MAX_EVIDENCE),
                          reveal=self.reveal, tier="D")]
        return [Check(name, True, f"{res.seconds:.2f}s under {limit:g}s budget",
                      reveal=self.reveal, tier="D")]


class Script(Oracle):
    """Run a stage-provided checker outside the writable workspace.

    The checker prints one JSON object per line:
        {"check": "name", "pass": true, "detail": "...", "evidence": "..."}
    Anything it prints that is not that shape is kept as evidence only.
    """
    kind = "script"

    def run(self, box: Sandbox) -> list[Check]:
        entry = self.config["entry"]
        # Resolved and quoted: cwd is the workspace, and a checker path with a
        # space must not become two arguments.
        oracle_dir = Path(box.oracle_dir).resolve()
        res = box.run(
            (f"BOARD_SEED={box.oracle_seed} " if box.oracle_seed is not None else "")
            + f"{self.config.get('interpreter', 'python3')} {shlex.quote(str(oracle_dir / entry))}",
            cwd=box.workspace,
            timeout=int(self.config.get("timeout_s", 180)),
        )
        return parse_script_output(res, self.reveal, entry,
                                   full_evidence=self.config.get("reveal_full_evidence", False))


class Differential(Script):
    """Tier E. Compare against a reference on seeded inputs.

    Same mechanism as Script, but got-vs-expected is the actual skill being
    tested, so withholding it teaches nothing. Reveal defaults to full.
    """
    kind = "differential"

    def __init__(self, config: dict, reveal: str = "full"):
        super().__init__(config, reveal)


class Mutation(Oracle):
    """Tier F. For 'write your own tests' stages.

    Inject each mutant into a copy of the workspace and run the agent's own
    test command. A mutant that the tests do not catch proves the tests are
    decorative, no matter how green they look.
    """
    kind = "mutation"

    def run(self, box: Sandbox) -> list[Check]:
        target = self.config["target"]
        test_cmd = self.config["test_command"]
        threshold = float(self.config.get("min_kill_rate", 0.6))
        original = (box.workspace / target).read_text(encoding="utf-8")

        killed, survived, invalid = 0, [], []
        for mutant in self.config["mutants"]:
            find, replace = mutant["find"], mutant["replace"]
            occurrences = original.count(find)
            if occurrences != 1:
                invalid.append(f"{mutant['name']} ({occurrences} matches for find)")
                continue
            scratch = box.root / f"_mut_{mutant['name']}"
            shutil.copytree(box.workspace, scratch)
            try:
                (scratch / target).write_text(original.replace(find, replace, 1),
                                              encoding="utf-8")
                started = time.monotonic()
                res = box.run(test_cmd, cwd=scratch,
                              timeout=int(self.config.get("timeout_s", 120)))
                if res.timed_out or res.exit_code == 0:
                    survived.append(mutant["name"])
                else:
                    killed += 1
            finally:
                shutil.rmtree(scratch, ignore_errors=True)

        total = killed + len(survived)
        if invalid:
            return [Check("mutation-setup", False,
                          "mutants are not well formed: " + "; ".join(invalid)[:MAX_DETAIL],
                          reveal=self.reveal, tier="F")]
        rate = killed / total if total else 0.0
        ok = rate >= threshold
        detail = (f"killed {killed}/{total} mutants ({rate:.0%}), "
                  f"need {threshold:.0%}")
        if survived:
            detail += "; survived: " + ", ".join(survived[:6])
        return [Check("mutation-score", ok, detail, reveal=self.reveal, tier="F")]


# --- registry ---------------------------------------------------------------

ORACLE_CLASSES: dict[str, type[Oracle]] = {
    c.kind: c for c in (FileExact, FileNormalized, JsonEqual, DiffBudget,
                        Command, Script, Differential, Mutation, Timing)
}


def build(spec) -> Oracle:
    cls = ORACLE_CLASSES.get(spec.kind)
    if cls is None:  # pragma: no cover - spec.py validates first
        raise ValueError(f"no oracle implementation for kind {spec.kind!r}")
    return cls(spec.config, spec.reveal)


def parse_script_output(res, reveal: str, entry: str, full_evidence: bool = False) -> list[Check]:
    """Turn a checker's stdout into Checks. Tolerant of noisy scripts."""
    checks: list[Check] = []
    noise: list[str] = []
    for line in (res.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            if line:
                noise.append(line)
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            noise.append(line)
            continue
        if not isinstance(payload.get("check"), str) or type(payload.get("pass")) is not bool:
            noise.append(line)
            continue
        checks.append(Check(
            name=sanitize(str(payload["check"]), 120),
            ok=payload["pass"],
            detail=sanitize(payload.get("detail", "")),
            evidence=sanitize(payload.get("evidence", ""), MAX_EVIDENCE),
            reveal=reveal,
            tier=payload.get("tier", "D"),
        ))
    if res.timed_out:
        checks.append(Check(f"{entry}:timeout", False,
                            "checker timed out", reveal=reveal))
    if checks and res.exit_code != 0 and not res.timed_out and all(c.ok for c in checks):
        checks.append(Check(f"{entry}:error", False,
                            f"checker exited {res.exit_code} without a failing check",
                            reveal=reveal))
    if not checks:
        checks.append(Check(f"{entry}:error", False,
                            "checker produced no verdict",
                            evidence=sanitize((res.stderr or res.stdout), MAX_EVIDENCE),
                            reveal=reveal))
    elif noise and full_evidence:
        checks.append(Check(f"{entry}:notes", True, "checker notes",
                            evidence=sanitize("\n".join(noise), MAX_EVIDENCE),
                            reveal="full"))
    return checks


# --- helpers ----------------------------------------------------------------

def _line_diff(got: list[str], want: list[str]) -> str:
    from difflib import unified_diff
    return "\n".join(unified_diff(want, got, fromfile="expected", tofile="produced",
                                  lineterm=""))[:MAX_EVIDENCE]


def _byte_evidence(got: bytes, want: bytes) -> str:
    first = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]),
                 min(len(got), len(want)))
    return f"first difference at byte {first}"


def _json_diff_paths(got, want, path: str = "$") -> list[str]:
    """Field paths that disagree. Names only — values stay withheld at minimal."""
    if type(got) is not type(want) and not (type(got) in (int, float)
                                            and type(want) in (int, float)):
        return [path]
    if isinstance(want, dict):
        out = []
        for key in sorted(want.keys() | got.keys()):
            if key not in want:
                out.append(f"{path}.{key} (unexpected)")
            elif key not in got:
                out.append(f"{path}.{key} (missing)")
            else:
                out += _json_diff_paths(got[key], want[key], f"{path}.{key}")
        return out
    if isinstance(want, list):
        if len(got) != len(want):
            return [f"{path} (length {len(got)} vs expected {len(want)})"]
        out = []
        for i, (g, w) in enumerate(zip(got, want)):
            out += _json_diff_paths(g, w, f"{path}[{i}]")
        return out
    return [] if got == want else [path]
