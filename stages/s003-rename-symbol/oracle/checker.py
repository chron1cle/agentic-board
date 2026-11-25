#!/usr/bin/env python3
"""Checks that the rename is complete. Prints one JSON verdict per line."""

import json
import sys
from pathlib import Path

OLD = "fetch_user"
NEW = "get_account"


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": ok, "detail": detail, "evidence": evidence}))


def sources():
    return sorted(p for p in Path(".").rglob("*.py"))


def main():
    files = sources()
    stale = [p for p in files if OLD in p.read_text(encoding="utf-8", errors="replace")]
    emit("old-name-gone", not stale,
         "old name still present" if stale else "no trace of the old name",
         "\n".join(str(p) for p in stale[:10]))

    accounts = Path("billing/accounts.py")
    defined = accounts.exists() and f"def {NEW}(" in accounts.read_text(encoding="utf-8")
    emit("new-name-defined", defined,
         "billing/accounts.py defines get_account" if defined
         else "billing/accounts.py does not define get_account")

    callers = [p for p in files if NEW in p.read_text(encoding="utf-8", errors="replace")]
    emit("callers-updated", len(callers) >= 4,
         f"{len(callers)} file(s) reference the new name, expected at least 4")

    init = Path("billing/__init__.py")
    if init.exists() and OLD in init.read_text(encoding="utf-8"):
        emit("package-export-clean", False, "__init__.py still exports the old name")
    else:
        emit("package-export-clean", True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
