#!/usr/bin/env python3
"""Migration hygiene: no legacy imports left, and the project's own suite is green."""

import json
import subprocess
import sys
from pathlib import Path


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": bool(ok), "detail": detail,
                      "evidence": str(evidence)[:1200]}))


def main():
    allowed = {"messenger/legacy.py"}
    offenders = []
    for path in sorted(Path(".").rglob("*.py")):
        rel = path.as_posix()
        if rel in allowed or rel.startswith("tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "legacy" in text or "Bus(" in text:
            offenders.append(rel)
    emit("no-legacy-imports", not offenders,
         "nothing outside messenger/legacy.py references the v1 bus" if not offenders
         else "still referencing v1",
         "\n".join(offenders[:10]))

    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
                          capture_output=True, text=True, timeout=180,
                          cwd=str(Path.cwd()))
    emit("project-suite-green", proc.returncode == 0,
         "the rewritten test suite passes" if proc.returncode == 0
         else f"suite exited {proc.returncode}",
         ((proc.stderr or "") + (proc.stdout or ""))[-1200:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
