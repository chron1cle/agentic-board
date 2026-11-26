from functools import lru_cache
from itertools import combinations
from support import batch, rng


def optimal_small(case):
    best = (0, 0, 0, [])
    for n in range(len(case["items"]) + 1):
        for subset in combinations(case["items"], n):
            ids = {j["id"] for j in subset}
            if any(set(j["requires"]) - ids for j in subset):
                continue
            if any({a, b} <= ids for a, b in case["incompatible"]):
                continue
            cost = sum(j["cost"] for j in subset)
            space = sum(j["space"] for j in subset)
            value = sum(j["value"] for j in subset)
            value += sum(v for a, b, v in case["bonuses"] if {a, b} <= ids)
            if cost <= case["budget"] and space <= case["capacity"]:
                best = min(best, (-value, cost, space, sorted(ids)))
    return dict(ids=best[3], value=-best[0], cost=best[1], space=best[2])


def large_case():
    # Each satellite requires its base. Each pair has exactly three legal
    # choices, allowing an independent budget recursion on this fixture family.
    ids = random.sample([f"p{i:02}" for i in range(48)], 48)
    items, bonuses, choices = [], [], []
    for a, b in zip(ids[::2], ids[1::2]):
        base = dict(id=a, cost=random.randint(1, 5), space=random.randint(1, 5),
                    value=random.randint(1, 8), requires=[])
        satellite = dict(id=b, cost=random.randint(1, 5), space=random.randint(1, 5),
                         value=random.randint(0, 8), requires=[a])
        bonus = random.randint(-9, 15)
        items.extend([base, satellite])
        bonuses.append([a, b, bonus])
        choices.append([(0, 0, 0, ()), (base["cost"], base["space"], base["value"], (a,)),
                        (base["cost"] + satellite["cost"], base["space"] + satellite["space"],
                         base["value"] + satellite["value"] + bonus, (a, b))])

    @lru_cache(None)
    def visit(i, money, room):
        if i == len(choices):
            return (0, 0, 0, ())
        candidates = []
        for c, s, v, keys in choices[i]:
            if c <= money and s <= room:
                nv, nc, ns, nk = visit(i + 1, money - c, room - s)
                candidates.append((nv-v, nc+c, ns+s, tuple(sorted(nk + keys))))
        return min(candidates)

    budget, capacity = random.randint(26, 40), random.randint(26, 40)
    negative, cost, space, names = visit(0, budget, capacity)
    visit.cache_clear()
    random.shuffle(items)
    return (dict(items=items, bonuses=bonuses, incompatible=[], budget=budget, capacity=capacity),
            dict(ids=list(names), cost=cost, space=space, value=-negative))


random = rng()
cases = []
for i in range(35):
    ids = random.sample(list("abcdefgh"), 8)
    items = [dict(id=k, cost=random.randint(1, 3), space=random.randint(1, 3), value=random.randrange(5),
                  requires=[a for a in ids[:j] if random.random() < 0.13]) for j, k in enumerate(ids)]
    pairs = list(combinations(ids, 2))
    case = dict(items=items, incompatible=random.sample(pairs, 4), budget=random.randrange(12),
                capacity=random.randrange(12), bonuses=[[a,b,random.randint(-9, 9)] for a,b in random.sample(pairs, 7)])
    cases.append((f"exhaustive-{i}", case, optimal_small(case)))
for i in range(3):
    cases.append((f"global-budgets-{i}", *large_case()))
batch("plan.py", cases)
