import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from support import emit, rng, run


def packed(rows):
    return "".join(json.dumps({"name": k, "value": rows[k]}, separators=(",", ":")) + "\n"
                   for k in sorted(rows)).encode()


random = rng()
with TemporaryDirectory() as tmp:
    root = Path(tmp)
    source, plan, dest = [root / name for name in ("legacy.json", "batches.json", "current.jsonl")]
    a, b, c, d, e = random.sample(["雪", "mill", "gear", "wheel", "press", "belt"], 5)
    rows = dict(zip([a, b, c], random.sample(range(-90, 90), 3)))
    source_bytes = json.dumps(rows).encode()
    source.write_bytes(source_bytes)
    valid = [[[a, b], [b, c], [c, a]], [], [[c, c], [a, d]], [[d, e], [e, d]]]
    # Use a chain ending in a free slot before the final two-way swap.
    valid[2].append([b, e])
    after = {c: rows[b], e: rows[c], d: rows[a]}
    bad_batches = [[[d, c]], [[a, b]], [[c, b], [c, a]], [[c, a], [e, a]]]
    for i, extra in enumerate([None, *bad_batches]):
        batch_bytes = json.dumps(valid if extra is None else [*valid, extra]).encode()
        plan.write_bytes(batch_bytes)
        for existing in (False, True):
            dest.unlink(missing_ok=True)
            old_link = root / "old-link"
            old_link.unlink(missing_ok=True)
            old = b"previous\n"
            if existing:
                dest.write_bytes(old)
                os.link(dest, old_link)
            for stop in (0, 1, len(rows), None):
                args = [] if stop is None else ["--interrupt", str(stop)]
                result = run("migrate.py", tmp, *args)
                expected_code = 2 if extra else (0 if stop is None else 75)
                wanted = packed(after) if expected_code == 0 else (old if existing else None)
                emit(f"batch-{i}-existing-{existing}-cut-{stop}",
                     result.returncode == expected_code and not result.stdout
                     and (dest.read_bytes() if dest.is_file() else None) == wanted
                     and (not existing or old_link.read_bytes() == old)
                     and source.read_bytes() == source_bytes and plan.read_bytes() == batch_bytes)
