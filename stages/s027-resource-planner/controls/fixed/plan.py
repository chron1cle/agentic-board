def answer(case):
    items = sorted(case["items"], key=lambda item: item["id"])
    indices = {item["id"]: i for i, item in enumerate(items)}
    dependencies = [set(indices[name] for name in item["requires"]) for item in items]
    conflicts = [set() for _ in items]
    for a, b in case["incompatible"]:
        conflicts[indices[a]].add(indices[b])
        conflicts[indices[b]].add(indices[a])
    remaining = [0] * (len(items) + 1)
    for i in reversed(range(len(items))):
        remaining[i] = remaining[i + 1] + items[i]["value"]
    best = (0, 0, [])

    def search(i, chosen, rejected, cost, value):
        nonlocal best
        if value + remaining[i] < -best[0]:
            return
        if i == len(items):
            candidate = (-value, cost, [items[j]["id"] for j in sorted(chosen)])
            best = min(best, candidate)
            return
        item = items[i]
        if (cost + item["cost"] <= case["budget"] and not conflicts[i] & chosen
                and not dependencies[i] & rejected):
            search(i + 1, chosen | {i}, rejected, cost + item["cost"], value + item["value"])
        if not any(i in dependencies[j] for j in chosen):
            search(i + 1, chosen, rejected | {i}, cost, value)

    search(0, set(), set(), 0, 0)
    return {"ids": best[2], "cost": best[1], "value": -best[0]}


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))
