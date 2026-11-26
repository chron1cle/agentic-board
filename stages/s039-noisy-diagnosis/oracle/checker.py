from functools import lru_cache
from support import batch, rng


def reference(case):
    cap, moves = case["cap"], case["moves"]
    # Keep all possible spent totals. Directly price a decision tree by its
    # worst terminal path, without combining costs from different paths.
    @lru_cache(None)
    def tree(paths):
        classes = {case["labels"][s] for s, _, _ in paths}
        if len(classes) == 1 and all(case["safe"][s] for s, _, _ in paths):
            return max(spent for s, errors, spent in paths), ()
        choices = []
        for j in range(len(moves[0])):
            if any(not moves[s][j] for s, _, _ in paths):
                continue
            events = [(obs, dest, used, spent+charge) for s, used, spent in paths
                      for obs, dest, charge in moves[s][j]]
            if any(spent > cap for obs, dest, used, spent in events):
                continue
            branches = []
            for reported in range(case["signals"]):
                branch = frozenset((dest, used+(obs != reported), spent) for obs, dest, used, spent in events
                                   if used+(obs != reported) <= case["errors"])
                if branch:
                    branches.append(tree(branch)[0])
            choices.append((max(branches), j))
        best = min((c for c, j in choices), default=cap+1)
        return best, tuple(j for c, j in choices if c == best)

    answers = []
    for start in case["starts"]:
        cost, probes = tree(frozenset((s, 0, 0) for s in start))
        answers.append(dict(credit=cost, probes=list(probes)) if cost <= cap else None)
    tree.cache_clear()
    return answers


random = rng()
cases = []
for i in range(32):
    labels = [0, 1, 0, 1, 0, 1]
    moves = []
    for s, label in enumerate(labels):
        same = [k for k, x in enumerate(labels) if x == label]
        moves.append([[(random.randrange(2), random.choice(same), random.randint(1, 4))
                       for _ in range(random.choice([0, 1, 1, 2]))] for _ in range(2)]
                     + [[(label, 4+label, 2 + (s % 3))]])
    case = dict(labels=labels, safe=[False, False, True, False, True, True], signals=2, moves=moves,
                errors=i%3, cap=6+i%4, starts=[[0,1], [0,2], [4,5], [1], [0,1,2,3], [1,2,4]])
    cases.append((f"noisy-trace-{i}", case, reference(case)))
# Two hidden paths have opposite expensive steps. Signals from the first two
# operations carry no class information. Later readings need a noisy majority.
for e in (0, 1, 2):
    heavy = random.randint(4, 8)
    labels = [0,1,0,1,0,1]
    moves = [[[[0,2+s, heavy if s==0 else 1]], []] for s in range(2)]
    moves.extend([[[[0,4+s, 1 if s==0 else heavy]], []] for s in range(2)])
    moves.extend([[[], [[s,4+s,1]]] for s in range(2)])
    minimum = heavy+1+2*e+1
    case = dict(labels=labels, safe=[False]*4+[True]*2, signals=2, errors=e, cap=minimum,
                moves=moves, starts=[[0,1], [4,5], [4], [0]])
    expected = [dict(credit=minimum, probes=[0]), dict(credit=2*e+1, probes=[1]),
                dict(credit=0, probes=[]), dict(credit=heavy+1, probes=[0])]
    cases.append((f"correlated-charges-{e}", case, expected))
batch("probe.py", cases)
