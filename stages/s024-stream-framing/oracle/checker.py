import json
from pathlib import Path
import selectors
import subprocess
import tempfile
import sys
from support import emit, read_json, rng, run

def frame(text):
    raw = text.encode()
    return len(raw).to_bytes(4, "big") + raw

random = rng()
values = ["", "雪", "a\nb", "🙂" * 12, "z" * 65536]
random.shuffle(values)
payload = b"".join(map(frame, values))
r = run("frames.py", input_data=payload)
emit("utf8-and-lengths", r.returncode == 0 and [read_json(line) for line in r.stdout.splitlines()] == values)

for i, bad in enumerate([b"\x00", b"\x00\x00\x00\x05ab", b"\x00\x01\x00\x01", b"\x00\x00\x00\x01\xff"]):
    r = run("frames.py", input_data=frame("kept") + bad)
    emit(f"preserves-prefix-{i}", r.returncode == 2 and r.stdout == b'"kept"\n')

with subprocess.Popen([sys.executable, "-I", str(Path("frames.py").resolve())],
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as child:
    with selectors.DefaultSelector() as watcher:
        watcher.register(child.stdout, selectors.EVENT_READ)
        try:
            for value in values:
                if value == "z" * 65536:
                    continue
                packet = frame(value)
                for offset in range(0, len(packet), 3):
                    child.stdin.write(packet[offset:offset + 3])
                    child.stdin.flush()
                if not watcher.select(1) or read_json(child.stdout.readline()) != value:
                    emit("incremental-output", False)
                    break
            else:
                emit("incremental-output", True)
        except (BrokenPipeError, ValueError):
            emit("incremental-output", False)
        finally:
            child.kill()

# Exercise a stream larger than the child address-space limit without loading
# it into the parent. The child still emits one record per input frame.
with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as destination:
    packet = frame("x" * 65536)
    records = 896
    for _ in range(records):
        source.write(packet)
    source.seek(0)
    limiter = (
        "import resource, runpy, sys; "
        "limit = 48 * 1024 * 1024; "
        "resource.setrlimit(resource.RLIMIT_AS, (limit, limit)); "
        "runpy.run_path(sys.argv[1], run_name='__main__')"
    )
    try:
        child = subprocess.run(
            [sys.executable, "-I", "-c", limiter, str(Path("frames.py").resolve())],
            stdin=source, stdout=destination, stderr=subprocess.DEVNULL, timeout=12,
        )
        destination.seek(0)
        emit("bounded-memory", child.returncode == 0 and sum(1 for _ in destination) == records)
    except subprocess.TimeoutExpired:
        emit("bounded-memory", False, "candidate did not finish the bounded-memory stream")
