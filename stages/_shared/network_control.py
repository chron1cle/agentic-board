"""Offline constraint intervals on a version tree, with rollback union-find."""
import json
import sys


class Components:
    def __init__(self, n, p):
        self.p = p
        self.parent = list(range(n))
        self.size = [1] * n
        self.mul = [1] * n
        self.add = [0] * n
        self.pin = [None] * n
        self.bad = [False] * n
        self.changes = []

    def find(self, u):
        m, c = 1, 0
        while u != self.parent[u]:
            m, c = m * self.mul[u] % self.p, (c + m * self.add[u]) % self.p
            u = self.parent[u]
        return u, m, c

    def remember(self, i):
        self.changes.append((i, self.parent[i], self.size[i], self.mul[i], self.add[i], self.pin[i], self.bad[i]))

    def rollback(self, marker):
        while len(self.changes) > marker:
            i, parent, size, mul, add, pin, bad = self.changes.pop()
            self.parent[i], self.size[i], self.mul[i], self.add[i], self.pin[i], self.bad[i] = (
                parent, size, mul, add, pin, bad)

    def fix(self, root, val):
        if self.pin[root] is not None and self.pin[root] != val:
            self.bad[root] = True
        self.pin[root] = val

    def link(self, edge):
        u, v, a, b = edge
        x, mu, cu = self.find(u)
        y, mv, cv = self.find(v)
        p = self.p
        # y = f*x + g
        inv = pow(mv, -1, p)
        f, g = a*mu*inv % p, (a*cu+b-cv)*inv % p
        if x == y:
            self.remember(x)
            if f != 1:
                self.fix(x, g * pow(1-f, -1, p) % p)
            elif g:
                self.bad[x] = True
            return
        if self.size[x] < self.size[y]:
            x, y = y, x
            f = pow(f, -1, p)
            g = -g*f % p
        self.remember(x)
        self.remember(y)
        self.parent[y], self.mul[y], self.add[y] = x, f, g
        self.size[x] += self.size[y]
        self.bad[x] |= self.bad[y]
        if self.pin[y] is not None:
            self.fix(x, (self.pin[y]-g) * pow(f, -1, p) % p)

    def query(self, u, v, given):
        x, mu, cu = self.find(u)
        y, mv, cv = self.find(v)
        if x != y:
            return "separate"
        root = (given-cu) * pow(mu, -1, self.p) % self.p
        if self.bad[x] or (self.pin[x] is not None and self.pin[x] != root):
            return "conflict"
        return (mv*root+cv) % self.p


def solve(case):
    versions = [[None, ["noop"]], *case["versions"]]
    count = len(versions)
    children = [[] for _ in versions]
    for i, (parent, _) in enumerate(versions[1:], 1):
        children[parent].append(i)

    size = 1 << (count-1).bit_length()
    buckets = [[] for _ in range(2*size)]
    def interval(start, end, edge):
        left, right = start+size, end+size
        while left < right:
            if left % 2:
                buckets[left].append(edge)
                left += 1
            if right % 2:
                right -= 1
                buckets[right].append(edge)
            left //= 2
            right //= 2

    active, order = {}, []
    stack = [(0, False, None)]
    while stack:
        i, exiting, restore = stack.pop()
        edit = versions[i][1]
        tick = len(order)
        op = edit[0]
        if exiting:
            if op == "link":
                edge, start = active.pop(edit[1])
                interval(start, tick, edge)
            elif op == "cut":
                active[edit[1]] = (restore, tick)
        else:
            if op == "link":
                edge = edit[2:] if len(edit) == 6 else [edit[2], edit[3], 1, edit[4]]
                active[edit[1]] = (edge, tick)
            elif op == "cut":
                restore, start = active.pop(edit[1])
                interval(start, tick, restore)
            order.append(i)
            stack.append((i, True, restore))
            stack.extend((child, False, None) for child in reversed(children[i]))

    queries = [[] for _ in versions]
    answers = [None] * len(case["queries"])
    for index, (version, *args) in enumerate(case["queries"]):
        queries[version].append((index, args))
    components = Components(case["n"], case.get("p", 2))
    def visit(node):
        marker = len(components.changes)
        for edge in buckets[node]:
            components.link(edge)
        if node >= size:
            if node-size < count:
                for index, args in queries[order[node-size]]:
                    answers[index] = components.query(*args) if len(args) == 3 else components.query(*args, 0)
        else:
            visit(2*node)
            visit(2*node+1)
        components.rollback(marker)
    visit(1)
    return answers


if __name__ == "__main__":
    for line in sys.stdin:
        print(json.dumps(solve(json.loads(line))))
