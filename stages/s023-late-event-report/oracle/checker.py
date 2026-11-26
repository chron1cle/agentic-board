from datetime import datetime, timedelta, timezone
from support import batch, rng

random = rng()
cases = [("empty", [], {})]
for i in range(25):
    events = []
    expected = {}
    for n in range(16):
        day = n % 3 + 1
        utc = datetime(2026, 3, day, random.choice([0, 23]), 30, tzinfo=timezone.utc)
        local = utc.astimezone(timezone(timedelta(minutes=random.choice([-720, -330, 0, 345, 840]))))
        value = random.randint(-100, 100) if (n + i) % 4 else None
        latest = {"id": str(n), "revision": 3, "timestamp": local.isoformat(), "value": value}
        events += [latest, dict(latest), dict(latest, revision=1, timestamp="2026-02-27T01:00:00+00:00", value=10)]
        if value is not None:
            bucket = expected.setdefault(f"2026-03-{day:02}", {"count": 0, "sum": 0})
            bucket["count"] += 1
            bucket["sum"] += value
    random.shuffle(events)
    cases.append((f"utc-corrections-{i}", events, expected))
batch("report.py", cases)
