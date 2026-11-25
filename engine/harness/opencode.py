"""Adapter for `opencode run --format json`.

The harness process needs the operator's real environment — it has to reach a
model provider with real credentials. Stage and oracle commands do not, and run
with a stripped environment instead. Keeping those two paths separate is the
point: the agent needs a key, the checker never does.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from .base import HarnessAdapter, HarnessRequest, HarnessResult

CONFIG_CANDIDATES = (
    "~/.config/opencode/opencode.jsonc",
    "~/.config/opencode/opencode.json",
)


def resolve_default_model() -> str:
    """Best-effort name of the configured default model, for honest labeling."""
    for candidate in CONFIG_CANDIDATES:
        path = Path(candidate).expanduser()
        if not path.exists():
            continue
        match = re.search(r'"model"\s*:\s*"([^"]+)"', path.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return "opencode-default"


class OpenCodeAdapter(HarnessAdapter):
    name = "opencode"

    def available(self) -> tuple[bool, str]:
        if shutil.which(self.bin_path or "opencode") is None:
            return False, "opencode binary not on PATH"
        return True, ""

    def label(self) -> str:
        return self.model or f"default ({resolve_default_model()})"

    def run(self, request: HarnessRequest) -> HarnessResult:
        binary = self.bin_path or "opencode"
        cmd = [binary, "run", "--format", "json", "--auto", "--archived",
               "--title", f"agentic-board {request.stage_id} a{request.attempt}"]
        model = request.model or self.model
        if model:
            cmd += ["--model", model]
        cmd.append(request.prompt)

        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, cwd=str(request.workspace), capture_output=True,
                text=True, errors="replace", timeout=request.timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raw = exc.stdout or ""
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            result = parse_opencode_stream(raw, 124, round(time.monotonic() - started, 2))
            result.timed_out = True
            result.error = "harness timed out"
            return result
        except (OSError, FileNotFoundError) as exc:
            return HarnessResult(exit_code=127, error=f"could not start harness: {exc}",
                                 seconds=round(time.monotonic() - started, 2))

        return parse_opencode_stream(proc.stdout, proc.returncode,
                                      round(time.monotonic() - started, 2), proc.stderr)


def _shrink(value, limit: int = 240):
    """Keep event payloads small enough to store in a run record."""
    if isinstance(value, dict):
        return {k: _shrink(v, 60) for k, v in list(value.items())[:8]}
    if isinstance(value, str):
        return value[:limit]
    return value


def parse_opencode_stream(raw: str, exit_code: int, seconds: float,
                          stderr: str = "") -> HarnessResult:
    """Turn opencode's JSONL into normalized events.

    Shape observed from v2.4.1: one JSON object per line with type in
    {step_start, tool_use, text, step_finish}; tool_use carries part.tool and
    part.state; step_finish carries part.tokens.
    """
    result = HarnessResult(exit_code=exit_code, seconds=seconds, raw=raw)
    text_parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        part = event.get("part") or {}
        if kind == "tool_use":
            state = part.get("state") or {}
            result.tool_calls += 1
            result.events.append({
                "type": "tool.call",
                "tool": part.get("tool", "?"),
                "status": state.get("status", ""),
                "input": _shrink(state.get("input")),
            })
        elif kind == "step_finish":
            tokens = part.get("tokens") or {}
            result.tokens += int(tokens.get("input", 0)) + int(tokens.get("output", 0)) \
                + int(tokens.get("reasoning", 0))
            result.events.append({"type": "step.finish", "reason": part.get("reason", "")})
        elif kind == "error":
            result.error = "OpenCode reported a session error"
        elif kind == "text":
            text_parts.append(part.get("text", ""))
            result.events.append({"type": "message"})
    result.text = "\n".join(t for t in text_parts if t)
    if exit_code != 0 and stderr:
        result.error = stderr.strip()[:500]
    return result
