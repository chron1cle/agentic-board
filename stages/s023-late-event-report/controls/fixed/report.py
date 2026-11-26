from datetime import datetime, timezone

def answer(events):
    highest = {}
    for event in events:
        old = highest.get(event["id"])
        if old is None or event["revision"] > old["revision"]:
            highest[event["id"]] = event
    report = {}
    for event in highest.values():
        if event["value"] is None:
            continue
        day = datetime.fromisoformat(event["timestamp"]).astimezone(timezone.utc).date().isoformat()
        bucket = report.setdefault(day, {"count": 0, "sum": 0})
        bucket["count"] += 1
        bucket["sum"] += event["value"]
    return report


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))
