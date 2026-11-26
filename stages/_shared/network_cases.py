from collections import deque
from support import batch, rng


def check(affine):
    random = rng()
    p = 11 if affine else 2

    def link(key, u, v, a, b):
        return ["link", key, u, v, a, b] if affine else ["link", key, u, v, b]

    def query(version, u, v, x):
        return [version, u, v, x] if affine else [version, u, v]

    def request(n, versions, queries):
        data = dict(n=n, versions=versions, queries=queries)
        if affine:
            data["p"] = p
        return data

    def inspect(edges, u, v, pin):
        adj = {}
        for a, b, m, c in edges.values():
            adj.setdefault(a, []).append((b, m, c))
            inv = pow(m, -1, p)
            adj.setdefault(b, []).append((a, inv, -inv*c))
        values = {u: pin}
        conflict = False
        queue = deque([u])
        while queue:
            a = queue.popleft()
            for b, m, c in adj.get(a, []):
                y = (m*values[a]+c) % p
                if b in values:
                    conflict |= values[b] != y
                else:
                    values[b] = y
                    queue.append(b)
        if v not in values:
            return "separate"
        return "conflict" if conflict else values[v]

    cases = []
    for trial in range(24):
        graphs, edits, queries, expected = [{}], [], [], []
        for i in range(1, 161):
            parent = i-1 if random.random() < 0.65 else random.randrange(i)
            graph = graphs[parent].copy()
            if graph and random.random() < 0.35:
                key = random.choice(sorted(graph))
                edit = ["cut", key]
                del graph[key]
            else:
                key = next(str(k) for k in range(200) if str(k) not in graph)
                u, v = random.randrange(8), random.randrange(8)
                a, b = random.randrange(1, p), random.randrange(p)
                edit = link(key, u, v, a, b)
                graph[key] = (u, v, a, b)
            edits.append([parent, edit])
            graphs.append(graph)
        for _ in range(500):
            version = random.randrange(len(graphs))
            u, v = random.randrange(8), random.randrange(8)
            x = random.randrange(p) if affine else 0
            queries.append(query(version, u, v, x))
            expected.append(inspect(graphs[version], u, v, x))
        cases.append((f"branch-consistency-{trial}", request(8, edits, queries), expected))

    # On the deep spine every sensor is an explicitly chosen affine function
    # of sensor 0. A cut separates its prefix and suffix, and a replacement
    # bridge composes a known change to the right-hand readings.
    n = 7800
    slopes = [1] + [random.randrange(1, p) for _ in range(n-1)]
    shifts = [0] + [random.randrange(p) for _ in range(n-1)]
    edits, queries, expected = [], [], []
    for i in range(1, n):
        m = slopes[i] * pow(slopes[i-1], -1, p) % p
        edits.append([i-1, link(str(i), i-1, i, m, (shifts[i]-m*shifts[i-1]) % p)])
    spine = n-1
    for i in range(1, n):
        key = str(i)
        edits.append([spine, ["cut", key]])
        cut = len(edits)
        edits.append([cut, link(key, 0, n-1, 1, i % p)])
        bridge = len(edits)
        edits.append([spine, link("extra", i, i, 1, 1)])
        bad = len(edits)
        x = random.randrange(p) if affine else 0
        for version, value in [(cut, "separate"), (bridge, (x+i) % p),
                               (bad, "conflict"), (spine, (slopes[-1]*x+shifts[-1]) % p)]:
            queries.append(query(version, 0, n-1, x))
            expected.append(value)
    order = random.sample(range(len(queries)), len(queries))
    cases.append(("deep-branch-history", request(n, edits, [queries[i] for i in order]),
                  [expected[i] for i in order]))
    batch("network.py", cases)
