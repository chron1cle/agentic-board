from collections import defaultdict
from datetime import datetime, timezone
import json
import sys


def report(case):
    latest = {}
    days = defaultdict(lambda: [0, 0])
    offset = 0
    answers = [None] * len(case["queries"])
    for index, (prefix, day) in sorted(enumerate(case["queries"]), key=lambda pair: pair[1][0]):
        while offset < prefix:
            event = case["events"][offset]
            offset += 1
            old = latest.get(event["id"])
            if old and event["revision"] <= old[0]:
                continue
            if old and old[2] is not None:
                days[old[1]][0] -= 1
                days[old[1]][1] -= old[2]
            utc = datetime.fromisoformat(event["timestamp"]).astimezone(timezone.utc).date().isoformat()
            value = event["value"]
            latest[event["id"]] = (event["revision"], utc, value)
            if value is not None:
                days[utc][0] += 1
                days[utc][1] += value
        count, total = days[day]
        answers[index] = {"count": count, "sum": total}
    return answers


for line in sys.stdin:
    print(json.dumps(report(json.loads(line))))
