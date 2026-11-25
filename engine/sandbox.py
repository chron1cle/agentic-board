"""Sandbox provisioning and execution.

An attempt always starts from a pristine workspace. That is what makes attempts
independent trials rather than one debugging session split into three, and the
independence is what the statistics in DESIGN.md depend on.

LocalSandbox runs on the host with directory isolation and a pinned
environment. It is the default so the whole benchmark runs offline with no
daemon. A container-backed sandbox can be dropped in behind the same interface
when stages need harder isolation; nothing above this module assumes host
execution.

TRUST BOUNDARY, stated plainly: LocalSandbox stops accidents and gives
determinism. It is not a security boundary. The agent and the engine run as the
same uid, so a determined agent can read files the engine tried to keep away
from it. Hidden-test stages are therefore a fairness measure, not a secret.
Container-backed execution is the real boundary and is required before any
stage's answer must stay confidential. See SECURITY.md.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from difflib import unified_diff
from pathlib import Path

# Pinned so "exact output" means the same thing on every machine. See DESIGN.md §3.
PINNED_ENV = {
    "LC_ALL": "C",
    "LANG": "C",
    "TZ": "UTC",
    "PYTHONHASHSEED": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUTF8": "1",
}

# Never let the operator's credentials reach the agent's environment, even by
# inheritance. Anything that looks like a secret is dropped.
SECRET_ENV_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH")

BINARY_SNIFF = 4096


@dataclass
class CommandResult:
    cmd: str
    exit_code: int
    stdout: str
    stderr: str
    seconds: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass
class FileDelta:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    changed_lines: int = 0

    @property
    def touched(self) -> list[str]:
        return sorted(set(self.added + self.removed + self.modified))


def _iter_files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in {".git", "__pycache__", ".pytest_cache"})
        for name in sorted(filenames):
            full = Path(dirpath) / name
            out.append(str(full.relative_to(root)))
    return out


def _read(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:BINARY_SNIFF]:
        return None
    return data.decode("utf-8", "replace")


def snapshot_hashes(root: Path, paths: list[str]) -> dict[str, str]:
    """Hash the given paths so a later attempt can prove nothing was tampered with."""
    hashes: dict[str, str] = {}
    for rel in paths:
        target = root / rel
        if target.is_dir():
            for rel_file in _iter_files(target):
                hashes[rel_file] = _hash_file(root / rel_file)
        elif target.exists():
            hashes[rel] = _hash_file(target)
        else:
            hashes[rel] = "<missing>"
    return hashes


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "<unreadable>"


class Sandbox:
    """One attempt's isolated workspace."""

    def __init__(self, root: Path, original: Path, protected: list[str] | None = None):
        self.root = Path(root)
        self.workspace = self.root / "workspace"
        self.original = Path(original)
        self.protected = list(protected or [])
        # Where the stage's hidden checkers live. The orchestrator points this
        # outside the attempt tree on purpose: an agent that runs `ls ..` from
        # its workspace should not find the answer key next to it.
        self.oracle_dir: Path = self.root / "_stage_oracle"
        self._baseline: dict[str, str] = {}
        self.history: list[CommandResult] = []

    # -- lifecycle ---------------------------------------------------------
    @classmethod
    def provision(cls, stage, dest: Path) -> "Sandbox":
        """Copy the stage fixture into dest. Byte-identical for every attempt."""
        dest = Path(dest)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        shutil.copytree(stage.workspace, dest / "workspace")
        shutil.copytree(stage.workspace, dest / "_original")
        box = cls(dest, dest / "_original", stage.protected)
        box._baseline = snapshot_hashes(box.workspace, box.protected)
        if stage.setup:
            script = stage.path / stage.setup
            if script.exists():
                box.run(f"bash {script}", cwd=box.workspace)
        return box

    def fingerprint(self) -> str:
        """Digest of the pristine workspace. Two attempts must match this."""
        return hashlib.sha256(
            "|".join(f"{p}:{_hash_file(self.original / p)}" for p in _iter_files(self.original)).encode()
        ).hexdigest()[:16]

    # -- execution ---------------------------------------------------------
    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items()
               if not any(h in k.upper() for h in SECRET_ENV_HINTS)}
        env.update(PINNED_ENV)
        env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")
        env["HOME"] = str(self.root)
        return env

    def run(self, cmd: str, cwd: Path | None = None, timeout: int = 120) -> CommandResult:
        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=str(cwd or self.workspace), env=self.env(),
                capture_output=True, text=True, errors="replace", timeout=timeout,
            )
            result = CommandResult(cmd, proc.returncode, proc.stdout, proc.stderr,
                                   time.monotonic() - started)
        except subprocess.TimeoutExpired as exc:
            result = CommandResult(cmd, 124,
                                   (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                                   (exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                                   time.monotonic() - started, timed_out=True)
        self.history.append(result)
        return result

    # -- integrity ---------------------------------------------------------
    def integrity_violations(self) -> list[str]:
        """Protected paths the agent modified or deleted. Disqualifies the run."""
        if not self._baseline:
            return []
        now = snapshot_hashes(self.workspace, self.protected)
        return sorted(p for p, digest in self._baseline.items() if now.get(p) != digest)

    # -- diffing -----------------------------------------------------------
    def delta(self) -> FileDelta:
        delta = FileDelta()
        before = set(_iter_files(self.original))
        after = set(_iter_files(self.workspace))
        delta.added = sorted(after - before)
        delta.removed = sorted(before - after)
        for rel in sorted(before & after):
            old = _read(self.original / rel)
            new = _read(self.workspace / rel)
            if old is None or new is None:
                if old != new:
                    delta.modified.append(rel)
                continue
            if old != new:
                delta.modified.append(rel)
                delta.changed_lines += _changed_lines(old, new)
        delta.added = [p for p in delta.added if not p.startswith("_original")]
        return delta

    def unified_diff(self, limit: int = 4000) -> str:
        lines: list[str] = []
        for rel in self.delta().modified:
            old = _read(self.original / rel)
            new = _read(self.workspace / rel)
            if old is None or new is None:
                continue
            lines += list(unified_diff(old.splitlines(), new.splitlines(),
                                       fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""))
        text = "\n".join(lines)
        return text[:limit]

    def read(self, rel: str) -> str | None:
        return _read(self.workspace / rel)

    def exists(self, rel: str) -> bool:
        return (self.workspace / rel).exists()


def normalize_text(text: str, ops: list[str]) -> str:
    """Apply the tier-B normalization vocabulary from DESIGN.md §3."""
    ops = ops or []
    if "strip-trailing-ws" in ops:
        text = "\n".join(line.rstrip() for line in text.splitlines())
    if "collapse-blank" in ops:
        kept: list[str] = []
        for line in text.splitlines():
            if line.strip() == "" and (not kept or kept[-1] == ""):
                continue
            kept.append(line)
        text = "\n".join(kept)
    if "strip-leading-ws" in ops:
        text = "\n".join(line.lstrip() for line in text.splitlines())
    if "sort-lines" in ops:
        text = "\n".join(sorted(text.splitlines()))
    if "trim-edges" in ops:
        text = text.strip("\n")
    return text


def _changed_lines(old: str, new: str) -> int:
    count = 0
    for line in unified_diff(old.splitlines(), new.splitlines(), lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            count += 1
        elif line.startswith("-") and not line.startswith("---"):
            count += 1
    return count
