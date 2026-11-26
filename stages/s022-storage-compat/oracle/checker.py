import json
from pathlib import Path
from tempfile import TemporaryDirectory
from support import emit, read_json, rng, run

random = rng()
with TemporaryDirectory() as tmp:
    path = Path(tmp) / "records.json"
    for i in range(4):
        amounts = [random.randint(-500, 500) for _ in range(12)]
        expected = {"a": amounts[::2], "b": amounts[1::2]}
        old = json.dumps({"entries": [{"account": "ab"[n % 2], "cents": v}
                                      for n, v in enumerate(amounts)]}).encode()
        path.write_bytes(old)
        before = run("records.py", "total", str(path), "b")
        emit(f"old-read-{i}", before.returncode == 0 and before.stdout == f"{sum(expected['b'])}\n".encode()
             and path.read_bytes() == old)
        converted = run("records.py", "translate", str(path))
        if converted.returncode:
            emit(f"migrate-{i}", False)
            continue
        migrated = path.read_bytes()
        emit(f"migrate-{i}", converted.stdout == b"migrated\n"
             and read_json(migrated) == {"version": 2, "accounts": expected})
        again = run("records.py", "translate", str(path))
        new = run("records.py", "total", str(path), "b")
        emit(f"current-is-read-only-{i}", again.returncode == new.returncode == 0
             and again.stdout == b"current\n" and new.stdout == before.stdout and path.read_bytes() == migrated)
    for i, invalid in enumerate([b"broken", b'{"entries":[{"account":"a","cents":true}]}',
                                 b'{"version":2,"accounts":{"a":[1.5]}}', b'{"entries":[],"extra":0}']):
        path.write_bytes(invalid)
        result = run("records.py", "translate", str(path))
        emit(f"reject-invalid-{i}", result.returncode == 2 and path.read_bytes() == invalid)
