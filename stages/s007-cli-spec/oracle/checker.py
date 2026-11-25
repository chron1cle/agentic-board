#!/usr/bin/env python3
"""Hidden acceptance tests for budget.py. Each check is one behaviour."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": ok, "detail": detail, "evidence": evidence[:1500]}))


def run(tool, args, cwd):
    proc = subprocess.run([PY, str(tool)] + args, cwd=str(cwd),
                          capture_output=True, text=True, timeout=30)
    return proc


def main():
    tool = Path.cwd() / "budget.py"
    if not tool.exists():
        emit("tool-exists", False, "budget.py is missing from the project root")
        return 0
    emit("tool-exists", True)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        proc = run(tool, ["balance"], cwd)
        emit("balance-empty", proc.returncode == 0 and proc.stdout.strip() == "balance: 0.00",
             f"got {proc.stdout.strip()!r}", proc.stderr[:300])

        outs = [run(tool, a, cwd).stdout.strip()
                for a in (["add", "12.50", "--note", "salary", "--date", "2026-11-01"],
                          ["add", "0.10"],
                          ["spend", "4.75", "--note", "coffee"])]
        emit("added-numbering", outs == ["added #1", "added #2", "added #3"],
             f"got {outs}")
        proc = run(tool, ["balance"], cwd)
        emit("balance-after", proc.stdout.strip() == "balance: 7.85",
             f"got {proc.stdout.strip()!r}")

        with tempfile.TemporaryDirectory() as tmp2:
            cwd2 = Path(tmp2)
            run(tool, ["add", "0.10"], cwd2)
            run(tool, ["add", "0.20"], cwd2)
            proc = run(tool, ["balance"], cwd2)
            emit("exact-money", proc.stdout.strip() == "balance: 0.30",
                 f"got {proc.stdout.strip()!r}")

        with tempfile.TemporaryDirectory() as tmp3:
            cwd3 = Path(tmp3)
            for args in (["add", "100.00", "--note", "salary", "--date", "2026-10-01"],
                         ["spend", "20.00", "--note", "rent", "--date", "2026-10-05"],
                         ["add", "50.00", "--note", "salary", "--date", "2026-11-02"],
                         ["spend", "5.00", "--date", "2026-11-03"]):
                run(tool, args, cwd3)
            proc = run(tool, ["report", "--by", "month"], cwd3)
            want = "2026-10 80.00\n2026-11 45.00"
            emit("report-by-month", proc.stdout.strip() == want,
                 f"got {proc.stdout.strip()!r}", f"want {want!r}")
            proc = run(tool, ["report", "--by", "note"], cwd3)
            want = "salary 150.00\n(none) -5.00\nrent -20.00"
            emit("report-by-note", proc.stdout.strip() == want,
                 f"got {proc.stdout.strip()!r}", f"want {want!r}")
            try:
                data = json.loads((cwd3 / "ledger.json").read_text())
                entries = data["entries"]
                ok = (isinstance(entries, list) and len(entries) == 4
                      and all(set(("amount", "note", "date")) <= set(e) for e in entries))
                emit("ledger-shape", ok, "entries carry amount/note/date",
                     json.dumps(entries)[:400])
            except Exception as exc:
                emit("ledger-shape", False, f"ledger.json unreadable: {exc}")

        cases = [
            (["add", "abc"], "bad-amount"),
            (["add", "1.234"], "too-many-decimals"),
            (["add", "-5"], "negative-amount"),
            (["add", "0"], "zero-amount"),
            (["add"], "missing-amount"),
            (["frobnicate"], "unknown-subcommand"),
            (["add", "5", "--date", "2026-13-01"], "bad-date"),
        ]
        bad = []
        for args, label in cases:
            proc = run(tool, args, cwd)
            if not (proc.returncode == 2 and proc.stderr.startswith("error: ")
                    and proc.stdout.strip() == ""):
                bad.append(f"{label}: exit={proc.returncode} out={proc.stdout.strip()!r} "
                           f"err={proc.stderr.strip()[:60]!r}")
        emit("error-handling", not bad, "all invalid inputs rejected with exit 2",
             "\n".join(bad[:6]))

        with tempfile.TemporaryDirectory() as tmp4:
            cwd4 = Path(tmp4)
            (cwd4 / "ledger.json").write_text("{not json at all")
            proc = run(tool, ["balance"], cwd4)
            emit("corrupt-ledger", proc.returncode == 3 and "ledger unreadable" in proc.stderr,
                 f"exit={proc.returncode} err={proc.stderr.strip()[:80]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
