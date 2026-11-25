#!/usr/bin/env python3
"""Hidden tests for the aggregation helper."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": bool(ok), "detail": detail,
                      "evidence": str(evidence)[:900]}))


def main():
    try:
        from pipeline import summarise
    except Exception as exc:
        emit("imports", False, f"pipeline does not import: {exc}")
        return 0
    emit("imports", True)

    records = [{"worker": "a", "ms": 10}, {"worker": "b", "ms": 20}, {"worker": "a", "ms": 30}]
    snapshot = [dict(r) for r in records]
    out = summarise(records)
    emit("per-worker-average", out.get("a") == 20.0 and out.get("b") == 20.0, f"got {out}")
    emit("total", out.get("__total__") == 60, f"got {out.get('__total__')!r}")
    emit("input-not-mutated", records == snapshot, f"caller's list became {records}")
    emit("empty-input", summarise([]) == {"__total__": 0}, f"got {summarise([])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
