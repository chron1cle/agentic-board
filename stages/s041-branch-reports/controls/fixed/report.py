from bisect import bisect_left
from collections import defaultdict
from math import isqrt
import json
import sys


class Sums:
    def __init__(self, size):
        self.tree = [0] * (size+1)

    def add(self, pos, change):
        pos += 1
        while pos < len(self.tree):
            self.tree[pos] += change
            pos += pos & -pos

    def prefix(self, end):
        total = 0
        while end:
            total += self.tree[end]
            end -= end & -end
        return total


def report(case):
    versions = [[None, []], *case["versions"]]
    children = [[] for _ in versions]
    dates = defaultdict(set)
    for index, (parent, edit) in enumerate(versions[1:], 1):
        children[parent].append(index)
        if edit[0] == "post":
            dates[edit[2]].add(edit[3])
    threshold = isqrt(len(versions)) + 1
    heavy = {a: sorted(d) for a,d in dates.items() if len(d)>threshold}
    weighted = Sums(case["days"])
    counts = Sums(case["days"])
    heavy_sums = {key: Sums(len(days)) for key,days in heavy.items()}
    light = defaultdict(dict)
    rates, rows = {}, {}

    def row_delta(row, sign):
        if row is None:
            return
        account, day, units = row
        value = sign * units
        counts.add(day, sign)
        if account in heavy:
            heavy_sums[account].add(bisect_left(heavy[account],day), value)
        else:
            active = light[account]
            active[day] = active.get(day,0) + value
            if not active[day]:
                del active[day]
            weighted.add(day, value*rates.get(account,1))

    def set_row(key, new):
        old = rows.pop(key, None)
        row_delta(old,-1)
        if new is not None:
            rows[key] = new
            row_delta(new,1)
        return old

    def set_rate(key, new):
        old = rates.get(key,1)
        if key not in heavy:
            for day, units in light[key].items():
                weighted.add(day,units*(new-old))
        rates[key] = new
        return old

    requests = [[] for _ in versions]
    for i,(version,lo,hi) in enumerate(case["queries"]):
        requests[version].append((i,lo,hi+1))
    answers = [None]*len(case["queries"])
    stack = [(0,False,None)]
    while stack:
        node, exiting, prior = stack.pop()
        edit = versions[node][1]
        if exiting:
            if edit:
                if edit[0] == "rate":
                    set_rate(edit[1],prior)
                else:
                    set_row(edit[1],prior)
            continue
        if edit:
            if edit[0] == "rate":
                prior = set_rate(edit[1],edit[2])
            else:
                prior = set_row(edit[1], edit[2:] if edit[0] == "post" else None)
        for i,lo,hi in requests[node]:
            value = weighted.prefix(hi) - weighted.prefix(lo)
            for key, days in heavy.items():
                sums = heavy_sums[key]
                value += rates.get(key,1)*(sums.prefix(bisect_left(days,hi))-sums.prefix(bisect_left(days,lo)))
            answers[i] = [counts.prefix(hi)-counts.prefix(lo), value]
        stack.append((node,True,prior))
        stack.extend((child,False,None) for child in children[node])
    return answers


for line in sys.stdin:
    print(json.dumps(report(json.loads(line))))
