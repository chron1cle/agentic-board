#!/usr/bin/env python3
"""Reference implementation of the budget CLI (used as the stage's fixed control)."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

LEDGER = "ledger.json"
AMOUNT = re.compile(r"^\d+(\.\d{1,2})?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def cents(text):
    if not AMOUNT.match(text):
        fail(f"invalid amount {text!r}")
    value = int(round(float(text) * 100))
    if value <= 0:
        fail("amount must be positive")
    return value


def fmt(value):
    sign = "-" if value < 0 else ""
    value = abs(value)
    return f"{sign}{value // 100}.{value % 100:02d}"


def load():
    path = Path(LEDGER)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        entries = data["entries"]
        if not isinstance(entries, list):
            raise ValueError
        for entry in entries:
            int(round(float(entry["amount"]) * 100))
            entry["date"]
        return entries
    except Exception:
        fail("ledger unreadable", 3)


def save(entries):
    Path(LEDGER).write_text(json.dumps({"entries": entries}, indent=2) + "\n")


def parse_flags(rest):
    note, date = None, "2026-11-24"
    i = 0
    while i < len(rest):
        flag = rest[i]
        if flag not in ("--note", "--date") or i + 1 >= len(rest):
            fail(f"unexpected argument {flag!r}")
        if flag == "--note":
            note = rest[i + 1]
        else:
            date = rest[i + 1]
            if not DATE.match(date) or not _real_date(date):
                fail(f"invalid date {date!r}")
        i += 2
    return note, date


def _real_date(text):
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def main(argv):
    if not argv:
        fail("no command given")
    cmd, rest = argv[0], argv[1:]
    if cmd in ("add", "spend"):
        if not rest:
            fail("missing amount")
        amount = cents(rest[0])
        note, date = parse_flags(rest[1:])
        entries = load()
        entries.append({"amount": fmt(amount if cmd == "add" else -amount),
                        "note": note, "date": date})
        save(entries)
        print(f"added #{len(entries)}")
        return 0
    if cmd == "balance":
        total = sum(int(round(float(e["amount"]) * 100)) for e in load())
        print(f"balance: {fmt(total)}")
        return 0
    if cmd == "report":
        if rest[:1] != ["--by"] or len(rest) != 2 or rest[1] not in ("month", "note"):
            fail("usage: report --by month|note")
        entries = load()
        groups = {}
        for entry in entries:
            key = entry["date"][:7] if rest[1] == "month" else (entry.get("note") or "(none)")
            groups[key] = groups.get(key, 0) + int(round(float(entry["amount"]) * 100))
        items = sorted(groups.items()) if rest[1] == "month" else \
            sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
        for key, value in items:
            print(f"{key} {fmt(value)}")
        return 0
    fail(f"unknown command {cmd!r}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
