from support import batch, rng


def tick_trace(case):
    jobs = {job["id"]: job for job in case["jobs"]}
    ordered = sorted(jobs.values(), key=lambda j: (-j["priority"], j["id"]))
    left = {k: j["duration"] for k, j in jobs.items()}
    state = dict.fromkeys(jobs, "waiting")
    shifts = dict(case["shifts"])
    capacity = case["workers"]
    events = []
    for t in range(200):
        targets = {k for at, k in case["cancels"] if at == t and state[k] not in ("done", "dead")}
        for _ in jobs:
            targets.update(k for k, j in jobs.items() if targets.intersection(j["deps"]))
        for k in sorted(targets):
            if state[k] != "dead":
                state[k] = "dead"
                events.append([t, "cancel", k])
        for k in sorted(jobs):
            if state[k] == "running" and left[k] == 0:
                events.append([t, "finish", k])
                state[k] = "done"
        capacity = shifts.get(t, capacity)
        free = capacity
        selected = []
        for j in ordered:
            k = j["id"]
            if (state[k] in ("done", "dead") or j["crew"] > free or j["release"] > t
                    or any(state[d] != "done" for d in j["deps"])):
                continue
            selected.append(k)
            free -= j["crew"]
        for k in sorted(jobs):
            if state[k] == "running" and k not in selected:
                events.append([t, "pause", k])
                state[k] = "paused"
        for k in selected:
            if state[k] != "running":
                events.append([t, "resume" if state[k] == "paused" else "start", k])
                state[k] = "running"
            left[k] -= 1
        if all(s in ("done", "dead") for s in state.values()):
            return events
    raise AssertionError("fixture exceeded its tick bound")


random = rng()
cases = []
for i in range(38):
    names = random.sample(list("abcdefghijkl"), 10)
    jobs = [dict(id=k, priority=random.randrange(4), crew=random.randint(1, 4),
                 release=random.randrange(8), duration=random.randint(1, 6),
                 deps=[d for d in names[:n] if random.random() < 0.13]) for n, k in enumerate(names)]
    random.shuffle(jobs)
    shifts = [[2, 1], [4, 0], [7, 3], [10, 4]]
    random.shuffle(shifts)
    case = dict(jobs=jobs, workers=3, shifts=shifts,
                cancels=[[random.randrange(16), random.choice(names)] for _ in range(4)])
    events = tick_trace(case)
    cases.append((f"shift-trace-{i}", case, events))
    if i < 6:
        # Scaling every boundary and duration preserves the trace apart from time.
        scale = random.randint(50000000, 60000000)
        stretched = dict(case, jobs=[dict(j, release=j["release"]*scale, duration=j["duration"]*scale)
                                      for j in jobs], shifts=[[t*scale, c] for t, c in shifts],
                         cancels=[[t*scale, k] for t, k in case["cancels"]])
        cases.append((f"sparse-shift-trace-{i}", stretched, [[t*scale, op, k] for t, op, k in events]))
batch("schedule.py", cases)
