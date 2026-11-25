#!/usr/bin/env python3
"""Reference sessionizer. Hidden from the agent; used to generate expected CSV.

Kept deliberately literal: this is the specification in executable form, so the
differential oracle compares the agent's tool against it on unseen fixtures.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

GAP = timedelta(minutes=30)
FIELDS = 6


def parse(line: str):
    line = line.rstrip("\n")
    if not line.strip():
        return None
    parts = line.split(" ")
    if len(parts) != FIELDS:
        return None
    stamp, client, _method, path, status, latency = parts
    try:
        when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    if not path.startswith("/"):
        return None
    if not status.isdigit():
        return None
    if not latency.endswith("ms") or not latency[:-2].isdigit():
        return None
    if not client.replace(".", "").isdigit():
        return None
    return when, client, path


def sessionize(text: str) -> str:
    open_sessions: dict[str, dict] = {}
    done: list[dict] = []
    for line in text.splitlines():
        parsed = parse(line)
        if parsed is None:
            continue
        when, client, path = parsed
        current = open_sessions.get(client)
        if current is not None and when - current["last"] <= GAP:
            current["last"] = when
            current["requests"] += 1
            if path not in current["paths"]:
                current["paths"].append(path)
            continue
        if current is not None:
            done.append(current)
        open_sessions[client] = {"client": client, "first": when, "last": when,
                                 "requests": 1, "paths": [path]}
    done.extend(open_sessions.values())
    done.sort(key=lambda s: (s["first"], s["client"]))
    out = ["session_id,client,requests,first_seen,paths"]
    for index, session in enumerate(done, start=1):
        out.append(f"s{index},{session['client']},{session['requests']},"
                   f"{session['first'].strftime('%Y-%m-%dT%H:%M:%SZ')},{'|'.join(session['paths'])}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stdout.write(sessionize(sys.stdin.read()))
