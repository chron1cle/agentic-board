from itertools import combinations
from support import batch, rng

random = rng()
cases = []
for n in range(28):
    items = []
    for j in range(8):
        items.append(dict(id=f"i{j}", cost=random.randint(1, 8), value=random.randint(0, 8),
                          requires=[f"i{k}" for k in range(j) if random.random() < 0.16]))
    conflicts = [list(pair) for pair in combinations([x["id"] for x in items], 2) if random.random() < 0.13]
    budget = random.randrange(20)
    best = (0, 0, [])
    for count in range(len(items) + 1):
        for subset in combinations(items, count):
            ids = [item["id"] for item in subset]
            cost = sum(item["cost"] for item in subset)
            if cost <= budget and all(set(item["requires"]) <= set(ids) for item in subset) and not any(
                    set(pair) <= set(ids) for pair in conflicts):
                best = min(best, (-sum(item["value"] for item in subset), cost, ids))
    random.shuffle(items)
    cases.append((f"optimal-plan-{n}", {"budget": budget, "items": items, "incompatible": conflicts},
                  {"ids": best[2], "cost": best[1], "value": -best[0]}))
items = [dict(id=f"i{i:02}", value=1, cost=1, requires=[]) for i in range(25)]
# The absolute optimum is achieved by taking everything, so a solver can prune
# every excluded branch once it discovers this bound.
cases.append(("larger-plan", {"budget": 25, "items": items[::-1], "incompatible": []},
              {"ids": [item["id"] for item in items], "cost": 25, "value": 25}))
items = [dict(id="root", value=0, cost=1, requires=[])]
conflicts = []
for i in range(12):
    a, b = f"pair-{i:02}-a", f"pair-{i:02}-b"
    items.extend([dict(id=a, value=5, cost=1, requires=["root"]),
                  dict(id=b, value=9, cost=1, requires=["root"])])
    conflicts.append([a, b])
random.shuffle(items)
cases.append(("prerequisite-and-conflict-scale",
              {"budget": 13, "items": items, "incompatible": conflicts},
              {"ids": [f"pair-{i:02}-b" for i in range(12)] + ["root"],
               "cost": 13, "value": 108}))
batch("plan.py", cases)
