from collections import defaultdict
import heapq
import json
import sys


def solve(case):
    labels, starts = case["labels"], list(map(frozenset, case["starts"]))
    todo = list(starts)
    actions, parents, values = {}, defaultdict(list), {}
    heap = []
    while todo:
        group = todo.pop()
        if group in actions:
            continue
        actions[group] = {}
        if len({labels[s] for s in group}) == 1:
            heapq.heappush(heap, (0, tuple(sorted(group))))
            continue
        for j, price in enumerate(case["costs"]):
            branches = defaultdict(set)
            for s in group:
                options = case["moves"][s][j]
                if not options:
                    break
                for signal, dest in options:
                    branches[signal].add(dest)
            else:
                children = set(map(frozenset, branches.values()))
                actions[group][j] = children
                for child in children:
                    parents[child].append((group, j))
                todo.extend(children)
    # A parent action becomes safe to price once all its children have
    # finite settled values. Positive probe costs settle children first.
    waiting = {(g, j): len(children) for g, probes in actions.items() for j, children in probes.items()}
    while heap:
        cost, keys = heapq.heappop(heap)
        group = frozenset(keys)
        if group in values:
            continue
        values[group] = cost
        for parent, j in parents[group]:
            waiting[parent, j] -= 1
            if waiting[parent, j] == 0:
                c = case["costs"][j] + max(values[k] for k in actions[parent][j])
                heapq.heappush(heap, (c, tuple(sorted(parent))))
    answers = []
    for g in starts:
        if g not in values:
            answers.append(None)
            continue
        first = [j for j, children in actions[g].items()
                 if all(k in values for k in children)
                 and case["costs"][j] + max(values[k] for k in children) == values[g]]
        answers.append(dict(cost=values[g], probes=first))
    return answers


for line in sys.stdin:
    print(json.dumps(solve(json.loads(line))))
