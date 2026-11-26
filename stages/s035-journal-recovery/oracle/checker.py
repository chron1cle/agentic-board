import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from support import emit, read_json, rng, run


def encode(obj):
    return json.dumps(obj, indent=None, ensure_ascii=False).encode("utf-8")


def write(tx, key, revision, account, amount):
    return dict(op="write", tx=tx, id=key, expect=revision, account=account, amount=amount)


def command(op, tx):
    return dict(op=op, tx=tx)


def item(revision, account, amount):
    return dict(revision=revision, account=account, amount=amount)


def check(root, label, args, code, expected, preserve=False):
    path = root / "state.json"
    previous = path.read_bytes() if path.exists() else None
    alias = root / "previous"
    alias.unlink(missing_ok=True)
    if path.exists():
        os.link(path, alias)
    inputs = {p: p.read_bytes() for p in [root / "events.jsonl", root / "base.txt"] if p.exists()}
    result = run("pipeline.py", str(root), *args)
    current = path.read_bytes() if path.exists() else None
    emit(label, result.returncode == code and not result.stdout
         and (previous is None or alias.read_bytes() == previous)
         and all(p.exists() and p.read_bytes() == raw for p, raw in inputs.items())
         and (current == previous if preserve else current is not None and read_json(current) == expected))


random = rng()
for legacy in (0, 1, 2):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        source, path = root / "events.jsonl", root / "state.json"
        a, b, c = random.sample(list("abcdefgh"), 3)
        x, y = random.sample(["north", "south", "east", "west"], 2)
        v = random.randint(2, 99)
        t, u = "青", "mill"
        base = 13 if legacy else 0
        initial = {a: item(1, x, v)} if legacy else {}
        rev = 1 if legacy else 0
        initial_sums = {x: v} if legacy else {}
        if legacy:
            (root / "base.txt").write_text(str(base))
            old = dict(cursor=base, items=initial) if legacy == 1 else dict(
                version=2, offset=base, totals=initial_sums, items=initial)
            path.write_bytes(encode(old))

        # Declare expected state transitions alongside the journal. Check every
        # restart boundary, including open transactions and their original order.
        first = write(t, a, rev, y, v)
        again = write(t, a, rev+1, y, None)
        credit = write(u, b, 0, x, -v)
        stale = write(u, a, rev, x, 2*v)
        restore = write(t, a, rev+2, x, v)
        zero = write(t, c, 0, x, -v)
        dead = {a: item(rev+2, y, None)}
        restored = {a: item(rev+3, x, v), c: item(1, x, -v)}
        steps = [
            (command("begin", t), {t: []}, initial, initial_sums, 0),
            (first, {t: [first]}, initial, initial_sums, 0),
            (command("begin", u), {t: [first], u: []}, initial, initial_sums, 0),
            (credit, {t: [first], u: [credit]}, initial, initial_sums, 0),
            (again, {t: [first, again], u: [credit]}, initial, initial_sums, 0),
            (stale, {t: [first, again], u: [credit, stale]}, initial, initial_sums, 0),
            (command("commit", t), {u: [credit, stale]}, dead, {}, 0),
            (command("commit", u), {}, dead, {}, 1),
            (command("begin", t), {t: []}, dead, {}, 1),
            (restore, {t: [restore]}, dead, {}, 1),
            (zero, {t: [restore, zero]}, dead, {}, 1),
            (command("commit", t), {}, restored, {x: 0}, 1),
            (command("begin", u), {u: []}, restored, {x: 0}, 1),
            (credit, {u: [credit]}, restored, {x: 0}, 1),
            (command("abort", u), {}, restored, {x: 0}, 1),
        ]
        rows = [encode(s[0]) + b"\n" for s in steps]
        # Split inside a multibyte transaction id, then later withhold just
        # the newline of a syntactically complete last record.
        cut = rows[0].index(t.encode()) + 1
        source.write_bytes(rows[0][:cut])
        check(root, f"partial-utf8-{legacy}", [], 75, None, preserve=True)
        source.write_bytes(b"".join(rows)[:-1])
        check(root, f"zero-budget-{legacy}", ["--steps", "0"], 75, None, preserve=True)
        for i, (_, pending, items, sums, rejected) in enumerate(steps, start=1):
            expected = dict(version=3, offset=base+i, items=items, totals=sums, open=pending, rejected=rejected)
            if i == len(steps):
                check(root, f"missing-newline-{legacy}", [], 75, None, preserve=True)
                with source.open("ab") as handle:
                    handle.write(b"\n")
            check(root, f"restart-{legacy}-{i}", ["--steps", "1"],
                  0 if i == len(steps) else 75, expected)
            if i == 5:
                base_file = root / "base.txt"
                base_file.write_text(str(base + i))
                source.write_bytes(b"".join(rows[i:])[:-1])
        check(root, f"idempotent-{legacy}", [], 0, None, preserve=True)
        # A program that always consumes one line can pass the one-step
        # restarts. Also drive it through a batch containing competing commits.
        source.write_bytes(b"".join(rows))
        (root / "base.txt").write_text(str(base))
        before_batch = dict(version=3, offset=base, items=initial, totals=initial_sums,
                            open={}, rejected=0)
        path.write_bytes(encode(before_batch))
        check(root, f"interleaved-batch-{legacy}", ["--steps", "8"], 75,
              dict(version=3, offset=base+8, items=dead, totals={}, open={}, rejected=1))
        check(root, f"unlimited-suffix-{legacy}", [], 0, expected)
        if legacy:
            path.write_bytes(encode(old))
            source.write_bytes(b"")
            check(root, f"upgrade-at-eof-{legacy}", [], 0, before_batch)
        path.unlink(missing_ok=True)
        if legacy:
            # The only available events start at a positive base.
            check(root, f"missing-prefix-{legacy}", [], 2, None, preserve=True)
        (root / "base.txt").write_text("0")
        source.write_bytes(b"")
        path.write_bytes(encode(dict(cursor=1, items={})))
        check(root, f"offset-ahead-{legacy}", [], 2, None, preserve=True)
        path.unlink(missing_ok=True)
        check(root, f"empty-{legacy}", [], 0,
              dict(version=3, offset=0, items={}, totals={}, open={}, rejected=0))
