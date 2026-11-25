#!/usr/bin/env python3
"""Hidden behavioural tests for catalogue.py.

Reveal level is full: this stage is differential-style, so showing got-vs-wanted
is the point of the feedback rather than an answer leak.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": ok, "detail": detail, "evidence": evidence}))


def main():
    try:
        import catalogue
    except Exception as exc:
        emit("imports", False, f"catalogue.py does not import: {exc}")
        return 0
    emit("imports", True)

    cases = [
        ("page_count", [(0, 10), (1, 10), (10, 10), (11, 10), (20, 10), (95, 10)]),
        ("span_length", [(1, 1), (0, 10), (5, 4)]),
    ]
    for fn, argsets in cases:
        want = {"page_count": lambda t, p: -(-t // p), "span_length": lambda lo, hi: hi - lo + 1}[fn]
        bad = []
        for args in argsets:
            expected = want(*args)
            try:
                got = getattr(catalogue, fn)(*args)
            except Exception as exc:
                bad.append(f"{fn}{args} raised {type(exc).__name__}")
                continue
            if got != expected:
                bad.append(f"{fn}{args} -> {got!r}, expected {expected!r}")
        emit(fn, not bad, "all cases correct" if not bad else f"{len(bad)} case(s) wrong",
             "\n".join(bad[:8]))

    items = list(range(1, 26))
    pages = [(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
             (2, [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]),
             (3, [21, 22, 23, 24, 25]),
             (4, [])]
    bad = []
    for page, expected in pages:
        try:
            got = catalogue.page_items(items, page, 10)
        except Exception as exc:
            bad.append(f"page_items(page={page}) raised {type(exc).__name__}")
            continue
        if got != expected:
            bad.append(f"page_items(page={page}) -> {got!r}, expected {expected!r}")
    emit("page_items", not bad, "all pages correct" if not bad else f"{len(bad)} page(s) wrong",
         "\n".join(bad[:8]))

    top_cases = [([3, 1, 2], 2, [3, 2]), ([5, 4, 3, 2, 1], 5, [5, 4, 3, 2, 1]),
                 ([7], 3, [7]), ([], 3, [])]
    bad = []
    for pool, n, expected in top_cases:
        try:
            got = catalogue.top_n(pool, n)
        except Exception as exc:
            bad.append(f"top_n({pool}, {n}) raised {type(exc).__name__}")
            continue
        if got != expected:
            bad.append(f"top_n({pool}, {n}) -> {got!r}, expected {expected!r}")
    emit("top_n", not bad, "all cases correct" if not bad else f"{len(bad)} case(s) wrong",
         "\n".join(bad[:8]))

    run_cases = [([1, 2, 3], [1, 3, 6]), ([5], [5]), ([], []), ([2, -2, 4], [2, 0, 4])]
    bad = []
    for values, expected in run_cases:
        try:
            got = catalogue.running_totals(values)
        except Exception as exc:
            bad.append(f"running_totals({values}) raised {type(exc).__name__}")
            continue
        if got != expected:
            bad.append(f"running_totals({values}) -> {got!r}, expected {expected!r}")
    emit("running_totals", not bad, "all cases correct" if not bad else f"{len(bad)} case(s) wrong",
         "\n".join(bad[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
