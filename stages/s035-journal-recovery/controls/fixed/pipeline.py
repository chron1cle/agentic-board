import argparse
import json
from pathlib import Path
from checkpoint import save
from state import read_state, update


def replay(root, steps):
    path = root / "state.json"
    base_file = root / "base.txt"
    base = int(base_file.read_text()) if base_file.exists() else 0
    state = read_state(path)
    with (root / "events.jsonl").open("rb") as stream:
        skip = state["offset"] - base
        if skip < 0:
            return 2
        for _ in range(skip):
            if not stream.readline().endswith(b"\n"):
                return 2
        for consumed, raw in enumerate(stream):
            if consumed == steps or not raw.endswith(b"\n"):
                return 75
            update(state, json.loads(raw))
            save(path, state)
    if not path.exists() or json.loads(path.read_bytes()).get("version") != 3:
        save(path, state)
    return 0


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--steps", type=int)
args = parser.parse_args()
raise SystemExit(replay(args.directory, args.steps))
