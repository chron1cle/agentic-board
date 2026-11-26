from itertools import combinations
from support import batch, rng


def exhaustive(case):
    best = None
    for n in range(len(case["items"])+1):
        for rows in combinations(case["items"], n):
            keys = {r["id"] for r in rows}
            if any(a in keys and b not in keys for a,b in case["requires"]):
                continue
            if any(a in keys and b in keys for a,b in case["incompatible"]):
                continue
            c = sum(r["cost"] for r in rows)
            s = sum(r["space"] for r in rows)
            if c > case["budget"] or s > case["capacity"]:
                continue
            v = sum(r["value"] for r in rows) + sum(x for a,b,x in case["bonuses"] if {a,b} <= keys)
            rank = (-v,c,s)
            if best is None or rank < best:
                best, winners = rank, []
            if rank == best:
                winners.append(keys)
    return dict(value=-best[0],cost=best[1],space=best[2],ways=len(winners),
                ids=min(sorted(w) for w in winners),required=sorted(set.intersection(*winners)))


random = rng()
cases = []
for trial in range(48):
    names = random.sample(list("abcdefghijkl"), 10)
    bags = [[-1, names[:3]]]
    for k in names[3:]:
        parent = random.randrange(len(bags))
        prev = bags[parent][1]
        overlap = random.sample(prev, random.randrange(min(4,len(prev))+1))
        bags.append([parent, overlap+[k]])
    bags.extend([[0, names[:3]], [0, []]])
    pairs = sorted({tuple(sorted((a,b))) for _,keys in bags for a,b in combinations(keys,2)})
    random.shuffle(pairs)
    case = dict(items=[dict(id=k,cost=random.randint(1,4),space=random.randint(1,4),value=random.randint(-2,6))
                       for k in names], bags=bags, budget=random.randrange(18), capacity=random.randrange(18),
                requires=pairs[:2], incompatible=pairs[2:5],
                bonuses=[[a,b,random.randint(-6,8)] for a,b in pairs[4:]])
    cases.append((f"overlapping-bags-{trial}",case,exhaustive(case)))

# Each pair contributes one chosen variant to the optimum. All choices need
# the common hub. Pair ordering and interleaved ids do not change the count.
for pairs in (32, 45):
    names = random.sample([f"j{i:02}" for i in range(2*pairs)], 2*pairs)
    hub = "hub"
    items = [dict(id=hub,cost=1,space=1,value=-1)]
    bags = [[-1,[hub]]]
    requires, conflicts, bonuses, keys = [], [], [], [hub]
    for i,(a,b) in enumerate(zip(names[::2],names[1::2])):
        parent = 0 if i < 2 else (i//2)
        bags.append([parent,[hub,a,b]])
        bags.append([len(bags)-1,[hub,a,b]])
        conflicts.append([a,b])
        requires.extend([[a,hub],[b,hub]])
        for j in (a,b):
            items.append(dict(id=j,cost=1,space=1,value=1))
            bonuses.append([j,hub,2])
        keys.append(min(a,b))
    case = dict(items=items,bags=bags,budget=pairs+1,capacity=pairs+1,
                requires=requires,incompatible=conflicts,bonuses=bonuses)
    cases.append((f"shared-hub-{pairs}",case,dict(ids=sorted(keys),required=[hub],ways=pow(2,pairs,1000000007),
                                                   cost=pairs+1,space=pairs+1,value=3*pairs-1)))
batch("plan.py",cases)
