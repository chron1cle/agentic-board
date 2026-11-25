#!/usr/bin/env python3
"""Differential checker: run the agent's sessionize.py against hidden fixtures."""

import json
import subprocess
import sys
from difflib import unified_diff
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = sorted((HERE / "fixtures").glob("*.log"))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": ok, "detail": detail, "evidence": evidence[:1800]}))


def main():
    tool = Path.cwd() / "sessionize.py"
    if not tool.exists():
        emit("tool-exists", False, "sessionize.py is missing from the project root")
        return 0
    emit("tool-exists", True)

    failures = 0
    for fixture in FIXTURES:
        expected = (fixture.with_suffix(".csv")).read_text()
        try:
            proc = subprocess.run([sys.executable, "sessionize.py"], stdin=open(fixture),
                                  capture_output=True, text=True, timeout=60,
                                  cwd=str(Path.cwd()))
        except subprocess.TimeoutExpired:
            emit(f"fixture:{fixture.stem}", False, "tool did not finish within 60s")
            failures += 1
            continue
        if proc.returncode != 0:
            emit(f"fixture:{fixture.stem}", False,
                 f"tool exited {proc.returncode}",
                 (proc.stderr or "")[:800])
            failures += 1
            continue
        if proc.stdout == expected:
            emit(f"fixture:{fixture.stem}", True, "output matches")
        else:
            diff = "\n".join(unified_diff(expected.splitlines(), proc.stdout.splitlines(),
                                          fromfile="expected", tofile="yours", lineterm=""))
            emit(f"fixture:{fixture.stem}", False, "output differs", diff or
                 f"expected {expected!r} got {proc.stdout!r}")
            failures += 1

    emit("all-fixtures", failures == 0,
         "all fixtures matched" if failures == 0 else f"{failures} fixture(s) wrong")
    return 0


if __name__ == "__main__":
    sys.exit(main())
