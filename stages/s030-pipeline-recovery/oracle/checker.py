import json
from pathlib import Path
from tempfile import TemporaryDirectory
from support import emit, read_json, rng, run

def items(*events):
    return {event["id"]: {key: event[key] for key in ("revision", "account", "amount")}
            for event in events}

def expected(offset, records, sums):
    return {"version": 2, "offset": offset, "items": records, "totals": sums}

random = rng()
for i in range(3):
    value = random.randrange(2, 100)
    first = dict(id="a", revision=1, account="old", amount=value)
    move = dict(id="a", revision=2, account="new", amount=value * 2)
    credit = dict(id="b", revision=1, account="new", amount=-value * 2)
    remove = dict(id="a", revision=3, account="new", amount=None)
    events = [first, move, move, credit, first, remove, move]
    prefixes = [
        expected(1, items(first), {"old": value}),
        expected(2, items(move), {"new": value * 2}),
        expected(3, items(move), {"new": value * 2}),
        expected(4, items(move, credit), {"new": 0}),
        expected(5, items(move, credit), {"new": 0}),
        expected(6, items(remove, credit), {"new": -value * 2}),
        expected(7, items(remove, credit), {"new": -value * 2}),
    ]
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "events.jsonl"
        target = root / "state.json"
        raw = "".join(json.dumps(event) + "\n" for event in events).encode("utf-8")
        source.write_bytes(raw)
        initial = 1 if i else 0
        old = json.dumps({"cursor": 1, "items": items(first)}).encode()
        if initial:
            target.write_bytes(old)
        stopped = run("pipeline.py", tmp, "--steps", "0")
        emit(f"zero-step-{i}", stopped.returncode == 75
             and (target.read_bytes() == old if initial and target.exists() else not (initial or target.exists())))
        for offset in range(initial + 1, 8):
            r = run("pipeline.py", tmp, "--steps", "1")
            if not target.is_file() or r.returncode != (0 if offset == 7 else 75):
                emit(f"checkpoint-{i}-{offset}", False)
                break
            emit(f"checkpoint-{i}-{offset}", not r.stdout and read_json(target.read_bytes()) == prefixes[offset - 1]
                 and source.read_bytes() == raw)
        if target.exists() and read_json(target.read_bytes()) == prefixes[-1]:
            fixed = target.read_bytes()
            again = run("pipeline.py", tmp)
            emit(f"repeat-{i}", again.returncode == 0 and target.read_bytes() == fixed)
            with source.open("ab") as handle:
                handle.write((json.dumps(dict(credit, revision=2, amount=0)) + "\n").encode())
            grown = run("pipeline.py", tmp)
            emit(f"append-{i}", grown.returncode == 0 and read_json(target.read_bytes())
                 == expected(8, items(remove, dict(credit, revision=2, amount=0)), {"new": 0}))
