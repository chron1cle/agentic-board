from itertools import combinations
from support import batch, rng


def reference(case):
    labels = case["labels"]
    groups = [g for n in range(1, len(labels)+1) for g in combinations(range(len(labels)), n)]
    options = {}
    prices = {g: 0 for g in groups if len({labels[s] for s in g}) == 1}
    for g in groups:
        options[g] = {}
        for j, cost in enumerate(case["costs"]):
            if not all(case["moves"][s][j] for s in g):
                continue
            branches = {}
            for s in g:
                for signal, following in case["moves"][s][j]:
                    branches.setdefault(signal, set()).add(following)
            options[g][j] = [tuple(sorted(values)) for values in branches.values()]
    # Price strategies with at most h more probes, then extend the horizon.
    def price(g, j, table):
        children = options[g][j]
        if all(k in table for k in children):
            return case["costs"][j] + max(table[k] for k in children)
    while True:
        updated = prices.copy()
        for g in groups:
            for j in options[g]:
                c = price(g, j, prices)
                if c is not None and c < updated.get(g, float("inf")):
                    updated[g] = c
        if prices == updated:
            break
        prices = updated
    answers = []
    for start in case["starts"]:
        g = tuple(sorted(start))
        answers.append(None if g not in prices else
                       dict(cost=prices[g], probes=[j for j in options[g] if price(g, j, prices) == prices[g]]))
    return answers


random = rng()
cases = []
for i in range(30):
    labels = [0, 1, 2, 0, 1, 2]
    moves = []
    for s, label in enumerate(labels):
        same = [k for k, x in enumerate(labels) if x == label]
        row = [[(random.randrange(3), random.choice(same)) for _ in range(random.choice([0, 1, 1, 2]))]
               for j in range(3)]
        # Guaranteed expensive fallback in half the cases.
        row.append([(label, s)] if i % 2 == 0 or s < 3 else [])
        moves.append(row)
    case = dict(labels=labels, costs=[random.randint(1, 3) for _ in range(3)] + [9], moves=moves,
                starts=[[s] for s in range(6)] + [list(x) for x in combinations(range(6), 3)])
    cases.append((f"diagnosis-{i}", case, reference(case)))
# Distinguishing one of 16 hidden configurations takes exactly one measurement
# of each unknown bit. A useless self-loop never belongs in an optimal policy.
bits = 4
costs = random.sample(range(1, 12), bits)
moves = [[[[int(bool(state & 1 << j)), state]] for j in range(bits)] + [[[0, state]]] for state in range(16)]
starts, expected = [], []
for mask in range(16):
    starts.append([s for s in range(16) if s & ~mask == 0])
    used = [j for j in range(bits) if mask & 1 << j]
    expected.append(dict(cost=sum(costs[j] for j in used), probes=used))
cases.append(("independent-probes", dict(labels=list(range(16)), costs=costs+[1], moves=moves, starts=starts), expected))
batch("probe.py", cases)
