def answer(case):
    jobs = {job["id"]: job for job in case["jobs"]}
    pending = set(jobs)
    active = {}
    finished = set()
    events = []
    t = 0
    while pending or active:
        requested = {name for tick, name in case["cancels"] if tick == t and name in pending | active.keys()}
        doomed = set(requested)
        while True:
            more = {name for name in pending | active.keys() if doomed.intersection(jobs[name]["deps"])}
            if more <= doomed:
                break
            doomed |= more
        for name in sorted(doomed):
            pending.discard(name)
            active.pop(name, None)
            events.append([t, "cancel", name])
        for name in sorted(name for name in active if active[name] == t):
            del active[name]
            finished.add(name)
            events.append([t, "finish", name])
        candidates = sorted(
            (jobs[name] for name in pending
             if jobs[name]["release"] <= t and finished.issuperset(jobs[name]["deps"])),
            key=lambda job: (-job["priority"], job["id"]),
        )
        for job in candidates[:case["workers"] - len(active)]:
            name = job["id"]
            pending.remove(name)
            active[name] = t + job["duration"]
            events.append([t, "start", name])
        t += 1
    return events


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))
