`README.md` in this directory is the ticket queue and the docstrings in
`pipeline/` are the contract. Both are correct; the code is not.

Fix every ticket: the priority ordering, the shutdown hang, the lost tasks under
concurrency, the linear backoff, the swallowed failure, and the aggregation
errors.

Constraints:

- Keep all public names and signatures exactly as they are
  (`TaskQueue`, `Worker`, `retry`, `summarise`).
- Standard library only.
- `python3 -c "import pipeline"` must keep working from the project root.
- Do not delete functionality to make symptoms disappear — a queue that never
  blocks is not fixed, it is gone.
