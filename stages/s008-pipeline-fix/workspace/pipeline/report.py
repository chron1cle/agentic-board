"""Aggregation over completed work records."""


def summarise(records):
    """Average milliseconds per worker.

    `records` is a list of `{"worker": str, "ms": int}` dicts. Returns a dict
    mapping worker name to its average `ms` as a float, plus a `"__total__"` key
    holding the sum of all `ms`. The caller's list must come back unchanged.
    """
    records.sort(key=lambda r: r["worker"])
    totals = {}
    counts = {}
    for record in records:
        worker = record["worker"]
        totals[worker] = totals.get(worker, 0) + record["ms"]
        counts[worker] = counts.get(worker, 0) + 1
    out = {"__total__": sum(r["ms"] for r in records)}
    for worker, total in totals.items():
        out[worker] = total / len(records)
    return out
