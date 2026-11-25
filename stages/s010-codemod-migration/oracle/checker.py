#!/usr/bin/env python3
"""Runs the migration suites in subprocesses so a hang cannot wedge the run."""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = [("config", "tests_config.py", 60), ("behaviour", "tests_behavior.py", 90),
          ("hygiene", "tests_hygiene.py", 240)]


def main():
    for group, filename, limit in SUITES:
        suite = HERE / filename
        try:
            proc = subprocess.run([sys.executable, str(suite)], cwd=str(Path.cwd()),
                                  capture_output=True, text=True, timeout=limit,
                                  env={"PYTHONPATH": str(Path.cwd()), "PATH": "/usr/bin:/bin"})
        except subprocess.TimeoutExpired:
            print(json.dumps({"check": f"{group}:suite", "pass": False,
                              "detail": f"suite did not finish within {limit}s"}))
            continue
        forwarded = 0
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            payload = json.loads(line)
            payload["check"] = f"{group}:{payload['check']}"
            print(json.dumps(payload))
            forwarded += 1
        if not forwarded:
            print(json.dumps({"check": f"{group}:suite", "pass": False,
                              "detail": "suite produced no verdicts",
                              "evidence": ((proc.stderr or "") + (proc.stdout or ""))[:1200]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
