"""Grade seeded engineering programs against precomputed answers."""
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import tempfile


def rng():
    return random.Random(int(os.environ["BOARD_SEED"]))


def limits():
    for key, maximum in [(resource.RLIMIT_AS, 768 << 20), (resource.RLIMIT_FSIZE, 32 << 20)]:
        _, hard = resource.getrlimit(key)
        limit = maximum if hard == resource.RLIM_INFINITY else min(hard, maximum)
        resource.setrlimit(key, (limit, limit))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "tier": "E", "pass": ok, "detail": detail, "evidence": evidence}))


def different(a, b):
    # JSON booleans and numbers are distinct even when Python compares them equal.
    return json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


def mismatch(data, actual, expected):
    detail = "result differs"
    given = json.dumps(data, ensure_ascii=False)
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return f"expected {len(expected)} answers, got {len(actual)}", ""
        i = next(i for i, (a, b) in enumerate(zip(actual, expected)) if different(a, b))
        detail = f"answer {i} differs"
        actual, expected = actual[i], expected[i]
        queries = data.get("queries", data.get("starts", []))
        if len(given) > 800 and i < len(queries):
            given = f"query {queries[i]}"
    return detail, f"expected {str(expected)[:220]}, got {str(actual)[:220]}, input {given[:800]}"


def batch(script, cases):
    raw = "".join(json.dumps(data) + "\n" for _, data, _ in cases).encode()
    env = {k: v for k, v in os.environ.items() if k != "BOARD_SEED"}
    with tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run(
                [sys.executable, "-E", "-s", "-B", str(Path(script).resolve())], input=raw,
                stdout=output, stderr=subprocess.DEVNULL, env=env, timeout=20, preexec_fn=limits,
            )
        except subprocess.TimeoutExpired:
            emit("candidate-runtime", False, "program exceeded the 20-second grading budget")
            return
        if result.returncode:
            emit("candidate-runtime", False, f"program exited {result.returncode}")
            return
        output.seek(0)
        for name, data, expected in cases:
            line = output.readline()
            if not line:
                emit("output-count", False, f"missing output for {name}")
                return
            try:
                actual = json.loads(line)
            except (ValueError, UnicodeError, RecursionError):
                emit(name, False, "invalid JSON output")
                continue
            if different(actual, expected):
                emit(name, False, *mismatch(data, actual, expected))
            else:
                emit(name, True)
        if output.read(1):
            emit("output-count", False, "unexpected output after the last answer")
