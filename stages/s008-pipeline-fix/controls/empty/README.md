# pipeline — three open tickets

The docstrings in `pipeline/` describe the intended contract and are correct.
The code does not do what they say. Three tickets are open:

**PIPE-412 — "workers pick up the wrong jobs."**
Reported by ops: tasks pushed with high priority are handled last, and two tasks
with the same priority come out in a different order than they went in.
Minimal repro:

    q = TaskQueue()
    q.push("low", 1); q.push("high", 9); q.push("mid", 5)
    print([q.pop(block=False) for _ in range(3)])
    # expected ['high', 'mid', 'low']

**PIPE-413 — "the dashboard hangs at shutdown."**
`join()` spins forever in some runs and returns too early in others. Under load
with several threads pushing and popping at once, tasks also go missing
completely: 8 threads × 500 pushes sometimes yields fewer than 4000 results.
Traceback from a `Ctrl-C` during the hang:

    File ".../pipeline/queue.py", line 34, in join
        while self._done < self._outstanding:

**PIPE-414 — "retries are linear and failures vanish."**
Backoff grows `0.1, 0.2, 0.3` instead of doubling, and a function that fails
every time makes `retry` return `None` so the caller never learns anything
failed. Separately, `summarise()` reports averages that are far too small, and
one caller found that their own list came back sorted.

Fix all three. Keep every public name and signature exactly as it is.
