from support import batch, rng

def job(name, release=0, duration=1, priority=0, deps=()):
    return dict(id=name, release=release, duration=duration, priority=priority, deps=list(deps))

random = rng()
cases = [
    ("cancel-wins-and-propagates", {"workers": 2, "jobs": [
        job("a", duration=2), job("b", deps=["a"]), job("d", deps=["b"]),
        job("c", duration=3)], "cancels": [[2, "a"]]},
     [[0, "start", "a"], [0, "start", "c"], [2, "cancel", "a"], [2, "cancel", "b"],
      [2, "cancel", "d"], [3, "finish", "c"]]),
    ("release-and-same-tick-dependencies", {"workers": 1, "jobs": [
        job("a", duration=2), job("b", priority=3), job("c", release=4, deps=["a"])],
        "cancels": [[2, "b"]]},
     [[0, "start", "b"], [1, "finish", "b"], [1, "start", "a"],
      [3, "finish", "a"], [4, "start", "c"], [5, "finish", "c"]]),
]
for i in range(25):
    duration = random.randint(1, 8)
    later = random.randint(1, 8)
    names = [f"a{i}", f"b{i}", f"c{i}", f"d{i}", f"e{i}"]
    a, b, c, d, e = names
    jobs = [job(a, duration=duration, priority=2), job(b, duration=duration),
            job(c, duration=later, deps=[a, b]), job(d, priority=1, deps=[a]),
            job(e, deps=[c])]
    random.shuffle(jobs)
    cases.append((f"two-worker-frontier-{i}", {"workers": 2, "jobs": jobs,
                  "cancels": [[duration + 1, c]]},
                  [[0, "start", a], [0, "start", b], [duration, "finish", a],
                   [duration, "finish", b], [duration, "start", d], [duration, "start", c],
                   [duration + 1, "cancel", c], [duration + 1, "cancel", e],
                   [duration + 1, "finish", d]]))
batch("schedule.py", cases)
