"""One-shot CLI execution and shared event parsing."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from .base import HarnessAdapter, HarnessRequest, HarnessResult, elapsed


def execute(argv, workspace, timeout, *, stdin=None, env=None):
    started = time.monotonic()
    try:
        with subprocess.Popen(
            argv, cwd=workspace, env=env, start_new_session=True,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        ) as process:
            timed_out = False
            try:
                stdout, stderr = process.communicate(stdin, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                stop_group(process.pid)
                stdout, stderr = process.communicate()
            finally:
                stop_group(process.pid)
            return HarnessResult(
                exit_code=124 if timed_out else process.returncode,
                seconds=elapsed(started), raw=stdout, timed_out=timed_out, tokens_reported=False,
                error=stderr.strip()[:500] if process.returncode else "",
            )
    except OSError as exc:
        return HarnessResult(exit_code=127, seconds=elapsed(started),
                             error=f"could not start harness: {exc}")


def stop_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def object_value(value):
    return value if isinstance(value, dict) else {}


def json_object(text):
    try:
        return object_value(json.loads(text))
    except ValueError:
        return {}


def objects(raw):
    for line in raw.splitlines():
        event = json_object(line)
        if event:
            yield event


def token_count(usage, totals, components):
    usage = object_value(usage)
    for key in totals:
        if count(usage.get(key)) is not None:
            return usage[key]
    values = [count(usage.get(key)) for key in components]
    return sum(value for value in values if value is not None) if any(
        value is not None for value in values) else None


def count(value):
    return value if type(value) is int and value >= 0 else None


class ToolEvents:
    def __init__(self, result):
        self.result = result
        self.seen = set()

    def add(self, name, identifier=None):
        if isinstance(identifier, (str, int)):
            if identifier in self.seen:
                return
            self.seen.add(identifier)
        self.result.tool_calls += 1
        self.result.events.append({"type": "tool.call", "tool": name if isinstance(name, str) else "tool"})


class ProcessAdapter(HarnessAdapter):
    executables: tuple[str, ...] = ()

    def binary(self):
        for name in (self.bin_path,) if self.bin_path else self.executables:
            path = shutil.which(name)
            if path:
                return str(Path(path).absolute())
        return None

    def available(self):
        if self.binary():
            return True, ""
        return False, f"executable unavailable: {self.bin_path or ' or '.join(self.executables)}"

    def label(self):
        return self.model or "configured default"

    def invocation(self, request, model):
        raise NotImplementedError

    def run(self, request: HarnessRequest):
        binary = self.binary()
        if not binary:
            return HarnessResult(exit_code=127, error=self.available()[1])
        args, stdin, env = self.invocation(request, request.model or self.model)
        result = execute([binary, *args], request.workspace, request.timeout_s, stdin=stdin, env=env)
        if result.raw or result.ok:
            self.read(result)
        return result
