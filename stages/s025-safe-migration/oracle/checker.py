import json
from pathlib import Path
from tempfile import TemporaryDirectory
from support import emit, read_json, rng, run

random = rng()
with TemporaryDirectory() as tmp:
    root = Path(tmp)
    destination = root / "current.jsonl"
    source = root / "legacy.json"
    values = {f"n-{i}": random.randrange(-999, 999) for i in reversed(range(8))}
    raw = (json.dumps(values) + "\n").encode()
    source.write_bytes(raw)
    for i in range(len(values) + 1):
        old = b'{"name":"previous","value":17}\n'
        if i % 2:
            destination.write_bytes(old)
        else:
            destination.unlink(missing_ok=True)
        r = run("migrate.py", tmp, "--interrupt", str(i))
        intact = destination.read_bytes() == old if i % 2 and destination.exists() else not (i % 2 or destination.exists())
        emit(f"interruption-{i}", r.returncode == 75 and not r.stdout and intact and source.read_bytes() == raw)
        result = run("migrate.py", tmp)
        if result.returncode or not destination.is_file():
            emit(f"retry-{i}", False)
            continue
        written = destination.read_bytes()
        expected = [{"name": key, "value": values[key]} for key in sorted(values)]
        rows = [read_json(line) for line in written.splitlines()]
        compact = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows).encode()
        emit(f"retry-{i}", rows == expected and written == compact and source.read_bytes() == raw)
        again = run("migrate.py", tmp)
        emit(f"repeat-{i}", again.returncode == 0 and destination.read_bytes() == written)
