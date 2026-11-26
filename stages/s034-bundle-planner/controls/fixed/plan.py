from itertools import combinations
import json
import sys


def plan(case):
    items = {item["id"]: item for item in case["items"]}
    neighbors = {key: set(item["requires"]) for key, item in items.items()}
    for a, b, *_ in case["incompatible"] + case["bonuses"]:
        neighbors[a].add(b)
    for a in neighbors:
        for b in list(neighbors[a]):
            neighbors[b].add(a)

    unseen = set(items)
    states = {(0, 0): (0, ())}
    while unseen:
        group = set()
        todo = [min(unseen)]
        while todo:
            key = todo.pop()
            if key in group:
                continue
            group.add(key)
            todo.extend(neighbors[key] - group)
        unseen -= group

        choices = []
        for n in range(len(group) + 1):
            for keys in combinations(sorted(group), n):
                ids = set(keys)
                if any(not ids.issuperset(items[k]["requires"]) for k in keys):
                    continue
                if any(a in ids and b in ids for a, b in case["incompatible"]):
                    continue
                value = sum(items[k]["value"] for k in keys)
                value += sum(v for a, b, v in case["bonuses"] if a in ids and b in ids)
                choices.append((sum(items[k]["cost"] for k in keys), sum(items[k]["space"] for k in keys),
                                value, keys))

        merged = {}
        for (cost, space), (negative, names) in states.items():
            for dc, ds, value, keys in choices:
                size = (cost + dc, space + ds)
                if size[0] > case["budget"] or size[1] > case["capacity"]:
                    continue
                candidate = (negative - value, tuple(sorted(names + keys)))
                if size not in merged or candidate < merged[size]:
                    merged[size] = candidate
        states = merged
    value, cost, space, ids = min((negative, cost, space, names)
                                  for (cost, space), (negative, names) in states.items())
    return dict(ids=ids, cost=cost, space=space, value=-value)


for line in sys.stdin:
    print(json.dumps(plan(json.loads(line))))
