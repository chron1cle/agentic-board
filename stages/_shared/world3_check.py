"""Run candidate programs separately and compare public-format outputs."""

import json
import os
from pathlib import Path
import random
import subprocess
import sys


def rng():
    return random.Random(int(os.environ["BOARD_SEED"]))


def emit(name, passed, detail=""):
    print(json.dumps({"check": name, "pass": bool(passed), "detail": detail, "tier": "D"}))


def run(script, *args, input_data=b"", cwd=None):
    env = {key: value for key, value in os.environ.items() if key != "BOARD_SEED"}
    try:
        return subprocess.run(
            [sys.executable, "-E", "-s", "-B", str(Path(script).resolve()), *args],
            cwd=cwd, input=input_data, capture_output=True, env=env, timeout=10,
        )
    except subprocess.TimeoutExpired:
        emit("candidate-runtime", False, "program exceeded the checker time limit")
        raise SystemExit(0)


def read_json(raw):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        return None


def batch(script, cases):
    """Cases are named input/output pairs. Candidate output cannot emit verdicts."""
    result = run(script, input_data="".join(json.dumps(data) + "\n" for _, data, _ in cases).encode())
    if result.returncode:
        emit("candidate-runtime", False, f"program exited {result.returncode}")
        return
    lines = result.stdout.splitlines()
    if len(lines) != len(cases):
        emit("output-count", False, "expected one output line per input line")
        return
    for (name, _, expected), line in zip(cases, lines):
        try:
            actual = json.loads(line)
        except (ValueError, UnicodeError):
            emit(name, False, "invalid JSON output")
            continue
        emit(name, json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True))
