from itertools import combinations
import json
import sys

MOD = 1000000007


def store(table, budget, record):
    value, ways, example, required = record
    old = table.get(budget)
    if old is None or value > old[0]:
        table[budget] = record
    elif value == old[0]:
        table[budget] = value, (old[1]+ways) % MOD, min(old[2], example), required & old[3]


def plan(case):
    bags = [set(keys) for _, keys in case["bags"]]
    items = {row["id"]: row for row in case["items"]}
    children = [[] for _ in bags]
    overlap = [set() for _ in bags]
    for i, (parent, _) in enumerate(case["bags"][1:], 1):
        children[parent].append(i)
        overlap[i] = bags[parent] & bags[i]
    rules = [[] for _ in bags]
    for mode in ("requires", "incompatible", "bonuses"):
        for a, b, *rest in case[mode]:
            owner = next(i for i, bag in enumerate(bags) if a in bag and b in bag)
            rules[owner].append((mode, a, b, rest[0] if rest else 0))

    tables = [{} for _ in bags]
    for i in reversed(range(len(bags))):
        for n in range(len(bags[i])+1):
            for subset in combinations(sorted(bags[i]), n):
                selected = set(subset)
                owned = selected - overlap[i]
                value = sum(items[k]["value"] for k in owned)
                for mode, a, b, bonus in rules[i]:
                    if mode == "requires" and a in selected and b not in selected:
                        break
                    if mode == "incompatible" and a in selected and b in selected:
                        break
                    if a in selected and b in selected:
                        value += bonus
                else:
                    cost = sum(items[k]["cost"] for k in owned)
                    space = sum(items[k]["space"] for k in owned)
                    if cost > case["budget"] or space > case["capacity"]:
                        continue
                    local = {(cost, space): (value, 1, tuple(sorted(owned)), owned)}
                    for child in children[i]:
                        compatible = tables[child].get(frozenset(overlap[child] & selected), {})
                        merged = {}
                        for (c, s), (v, w, ex, req) in local.items():
                            for (dc, ds), (dv, dw, dex, dreq) in compatible.items():
                                if c+dc <= case["budget"] and s+ds <= case["capacity"]:
                                    store(merged, (c+dc, s+ds),
                                          (v+dv, w*dw % MOD, tuple(sorted(ex+dex)), req | dreq))
                        local = merged
                    group = tables[i].setdefault(frozenset(overlap[i] & selected), {})
                    for budget, record in local.items():
                        store(group, budget, record)
        for child in children[i]:
            tables[child].clear()
    root = tables[0][frozenset()]
    cost, space = min(root, key=lambda k: (-root[k][0], k))
    value, ways, keys, required = root[cost, space]
    return dict(value=value, cost=cost, space=space, ways=ways, ids=keys, required=sorted(required))


for line in sys.stdin:
    print(json.dumps(plan(json.loads(line))))
