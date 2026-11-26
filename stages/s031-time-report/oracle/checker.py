from datetime import datetime, timedelta, timezone
from support import batch, rng


def snapshot(events, prefix, day):
    winners = {}
    for row in sorted(events[:prefix], key=lambda row: row["revision"]):
        winners[row["id"]] = row
    values = [row["value"] for row in winners.values() if row["value"] is not None
              and datetime.fromisoformat(row["timestamp"]).astimezone(timezone.utc).date().isoformat() == day]
    return {"count": len(values), "sum": sum(values)}


random = rng()
cases = [("empty", {"events": [], "queries": []}, [])]
days = [f"2030-01-{n:02}" for n in range(1, 5)]
for i in range(12):
    events = []
    for rev in range(1, 6):
        for key in range(6):
            utc = datetime(2030, 1, random.randint(1, 3), random.choice([0, 23]), tzinfo=timezone.utc)
            zone = timezone(timedelta(minutes=random.choice([-660, 345, 840])))
            event = dict(id=str(key), revision=rev, timestamp=utc.astimezone(zone).isoformat(),
                         value=random.choice([None, 0, random.randint(-80, 80)]))
            events.extend([event, event] if key % 2 else [event])
    random.shuffle(events)
    queries = [[p, day] for p in range(len(events) + 1) for day in days]
    queries.extend(queries[:8])
    random.shuffle(queries)
    cases.append((f"historical-days-{i}", dict(events=events, queries=queries),
                  [snapshot(events, p, day) for p, day in queries]))

# At every prefix the first cycle creates one item per arrival. Later cycles
# replace that same item's value by one more, giving a closed-form sum.
width = random.randint(80, 150)
events = [dict(id=str(i % width), revision=i // width + 1, timestamp="2030-01-02T01:00:00+02:00",
               value=i // width + 1) for i in range(16000)]
prefixes = list(range(len(events) + 1))
random.shuffle(prefixes)
cases.append(("many-historical-prefixes", dict(events=events, queries=[[p, days[0]] for p in prefixes]),
              [{"count": min(p, width), "sum": p} for p in prefixes]))
batch("report.py", cases)
