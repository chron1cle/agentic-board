"""Aggregation over completed work records."""


def summarise(records):
    """Average milliseconds per worker, plus a `__total__` sum."""
    totals = {}
    counts = {}
    for record in records:
        worker = record["worker"]
        totals[worker] = totals.get(worker, 0) + record["ms"]
        counts[worker] = counts.get(worker, 0) + 1
    out = {"__total__": sum(record["ms"] for record in records)}
    for worker, total in totals.items():
        out[worker] = total / counts[worker]
    return out
