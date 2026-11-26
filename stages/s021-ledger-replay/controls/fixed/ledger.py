from collections import defaultdict

def answer(events):
    by_id = defaultdict(set)
    for e in events:
        by_id[e["id"]].add((e["account"], e["seq"], e["delta"]))
    balances = defaultdict(int)
    conflicts = []
    for key, values in by_id.items():
        if len(values) > 1:
            conflicts.append(key)
        else:
            account, _, delta = next(iter(values))
            balances[account] += delta
    return {"balances": dict(balances), "conflicts": sorted(conflicts)}


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))
