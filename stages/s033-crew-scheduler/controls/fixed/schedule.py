import json
import sys


def schedule(case):
    jobs = {job["id"]: job for job in case["jobs"]}
    shifts = dict(case["shifts"])
    cancels = {}
    for at, key in case["cancels"]:
        cancels.setdefault(at, set()).add(key)
    boundaries = sorted(set(shifts) | set(cancels) | {j["release"] for j in jobs.values()}, reverse=True)
    capacity = case["workers"]
    remaining = {key: j["duration"] for key, j in jobs.items()}
    finished, seen, running = set(), set(), set()
    events = []
    now = 0
    while remaining:
        doomed = cancels.get(now, set()) & remaining.keys()
        while True:
            descendants = {key for key in remaining if doomed.intersection(jobs[key]["deps"])}
            if descendants <= doomed:
                break
            doomed |= descendants
        for key in sorted(doomed):
            events.append([now, "cancel", key])
            del remaining[key]
        for key in sorted(key for key in remaining if remaining[key] == 0):
            events.append([now, "finish", key])
            finished.add(key)
            del remaining[key]

        capacity = shifts.get(now, capacity)
        free = capacity
        picked = []
        for key in sorted(remaining, key=lambda k: (-jobs[k]["priority"], k)):
            job = jobs[key]
            if job["release"] <= now and finished.issuperset(job["deps"]) and job["crew"] <= free:
                free -= job["crew"]
                picked.append(key)
        for key in sorted((running & remaining.keys()) - set(picked)):
            events.append([now, "pause", key])
        for key in picked:
            if key not in running:
                events.append([now, "resume" if key in seen else "start", key])
                seen.add(key)
        running = set(picked)
        if not remaining:
            break
        while boundaries and boundaries[-1] <= now:
            boundaries.pop()
        times = ([boundaries[-1]] if boundaries else []) + [now + remaining[k] for k in running]
        following = min(times)
        for key in running:
            remaining[key] -= following - now
        now = following
    return events


for line in sys.stdin:
    print(json.dumps(schedule(json.loads(line))))
