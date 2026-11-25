"""Tier E oracle using queue-based relaxation over explicit switch sets."""

from collections import defaultdict, deque
import json
import os
import random
import subprocess
import sys


MAX_SWITCHES = 3
FIELDS = ('toggle', 'need_on', 'need_off')



def cross(edge, switches):
    if edge.get("need_on", -1) != -1 and edge["need_on"] not in switches:
        return None
    if edge.get("need_off") in switches:
        return None
    fee = edge["cost"]
    result = set(switches)
    if "toggle" in edge:
        result.symmetric_difference_update({edge["toggle"]})
    return (edge["v"], frozenset(result)), max(0, fee)


def expected(case):
    outgoing = defaultdict(list)
    for edge in case["edges"]:
        outgoing[edge["u"]].append(edge)

    initial = (case["start"], frozenset())
    distances = {initial: 0}
    pending = deque([initial])
    queued = {initial}
    while pending:
        state = pending.popleft()
        queued.remove(state)
        node, switches = state
        for edge in outgoing[node]:
            crossing = cross(edge, switches)
            if crossing is None:
                continue
            target, fee = crossing
            candidate = distances[state] + fee
            if target not in distances or candidate < distances[target]:
                distances[target] = candidate
                if target not in queued:
                    queued.add(target)
                    pending.append(target)

    required = frozenset(case.get("arrival_on", []))
    return min((fee for (node, state), fee in distances.items()
                if node == case["goal"] and required <= state),
               default=None)


def random_graph(rng, switches):
    nodes = rng.randint(2, 7)
    edges = []
    for _ in range(5 * nodes):
        edge = {"u": rng.randrange(nodes), "v": rng.randrange(nodes),
                "cost": rng.randrange(10)}
        for field in FIELDS:
            if rng.random() >= 0.22:
                continue
            first = rng.randrange(switches)
            if field in {"on_discount", "off_discount"}:
                edge[field] = [first, rng.randrange(12)]
            elif field in {"copy", "swap"}:
                edge[field] = [first, rng.randrange(switches)]
            else:
                edge[field] = first
        edges.append(edge)
    case = {"nodes": nodes, "switches": switches, "start": rng.randrange(nodes),
            "goal": rng.randrange(nodes), "edges": edges}
    if rng.random() < 0.5:
        case["arrival_on"] = [i for i in range(switches) if rng.randrange(2)]
    return case


def combinations():
    # Every switch vector can be reached at node zero via these self-loops.
    edges = [{"u": 0, "v": 0, "cost": 1, "toggle": i} for i in range(MAX_SWITCHES)]
    edges.extend({"u": i, "v": i + 1, "cost": 1, "need_on": i}
                 for i in range(MAX_SWITCHES))
    return {"nodes": MAX_SWITCHES + 1, "switches": MAX_SWITCHES,
            "start": 0, "goal": MAX_SWITCHES, "edges": edges,
            "arrival_on": list(range(MAX_SWITCHES))}


def full_width_graph(rng):
    case = random_graph(rng, MAX_SWITCHES)
    start = case["start"]
    case["edges"].extend(
        {"u": start, "v": start, "cost": rng.randint(1, 9), "toggle": bit}
        for bit in range(MAX_SWITCHES)
    )
    return case


def emit(name, passed, detail=""):
    print(json.dumps({"check": name, "pass": passed, "detail": detail, "tier": "E"}))


def main():
    witnesses = [('toggle',
      {'arrival_on': [0],
       'edges': [{'cost': 4, 'toggle': 0, 'u': 0, 'v': 1},
                 {'cost': 2, 'u': 1, 'v': 2},
                 {'cost': 9, 'u': 0, 'v': 2}],
       'goal': 2,
       'nodes': 3,
       'start': 0,
       'switches': 3},
      6),
     ('need_on',
      {'edges': [{'cost': 0, 'need_on': 1, 'u': 0, 'v': 2},
                 {'cost': 2, 'toggle': 1, 'u': 0, 'v': 0}],
       'goal': 2,
       'nodes': 3,
       'start': 0,
       'switches': 3},
      2),
     ('need_off',
      {'edges': [{'cost': 1, 'toggle': 2, 'u': 0, 'v': 1},
                 {'cost': 1, 'need_off': 2, 'u': 1, 'v': 2},
                 {'cost': 8, 'u': 0, 'v': 2}],
       'goal': 2,
       'nodes': 3,
       'start': 0,
       'switches': 3},
      8)]
    rng = random.Random(int(os.environ["BOARD_SEED"]))
    cases = [(name, case, answer) for name, case, answer in witnesses]
    for name, case, answer in cases:
        if expected(case) != answer:
            raise ValueError(f"inconsistent checker witness: {name}")

    for name, case in [
        ("start-is-goal", {"nodes": 1, "switches": 0, "start": 0, "goal": 0, "edges": []}),
        ("unreachable", {"nodes": 2, "switches": 0, "start": 0, "goal": 1, "edges": []}),
        ("switch-combinations", combinations()),
        ("full-width-0", full_width_graph(rng)),
        ("full-width-1", full_width_graph(rng)),
    ] + [("generated-" + str(i), random_graph(rng, rng.randint(1, min(4, MAX_SWITCHES))))
         for i in range(36)]:
        cases.append((name, case, expected(case)))

    try:
        proc = subprocess.run(
            [sys.executable, "-I", "route.py"],
            input="".join(json.dumps(case) + "\n" for _, case, _ in cases),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            env={key: value for key, value in os.environ.items() if key != "BOARD_SEED"},
        )
    except subprocess.TimeoutExpired:
        emit("route-runtime", False, "route.py exceeded 15 seconds")
        return
    if proc.returncode:
        emit("route-runtime", False, f"route.py exited {proc.returncode}")
        return

    output = proc.stdout.splitlines()
    if len(output) != len(cases):
        emit("output-lines", False, f"expected {len(cases)} output lines, got {len(output)}")
        return
    for (name, _, answer), line in zip(cases, output):
        try:
            got = json.loads(line)
        except ValueError:
            emit(name, False, "expected a JSON integer or null")
            continue
        emit(name, type(got) is type(answer) and got == answer)


if __name__ == "__main__":
    main()
