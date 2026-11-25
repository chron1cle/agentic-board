Build a command-line tool that turns an access log into a session report.

Write a program at `sessionize.py` in the project root. It reads a log from
**standard input** and writes CSV to **standard output**. Run as:

    python3 sessionize.py < input.log

## Input format

One request per line:

    2026-11-23T07:00:00Z 10.0.0.11 GET /api/orders 200 120ms

Fields, single-space separated: ISO-8601 UTC timestamp, client IP, method,
path, numeric status, latency ending in `ms`. Blank lines and lines that do not
have exactly these six fields in this shape are **skipped silently** — a
malformed line is not an error and must not appear in the output.

## Grouping into sessions

Process requests in the order they appear. A session is one client IP's run of
requests where each request is **no more than 30 minutes after the previous one
from that same IP**. A gap of more than 30 minutes starts a new session. The
first request from an IP always starts a session.

## Output format

Emit a header line, then one line per session:

    session_id,client,requests,first_seen,paths

- `session_id` — `s1`, `s2`, … numbered by `first_seen` ascending across all
  clients; when two sessions start at the same instant, order them by client IP
  as a string.
- `client` — the IP.
- `requests` — how many requests are in the session.
- `first_seen` — timestamp of the session's first request, exactly as it
  appeared in the log.
- `paths` — the distinct paths in the session, in order of first appearance,
  joined with `|`.

Use `\n` line endings, no quoting unless a field would contain a comma (none
will), and no trailing blank line beyond the final newline.

Nothing else may be printed on stdout. Do not use third-party packages.
