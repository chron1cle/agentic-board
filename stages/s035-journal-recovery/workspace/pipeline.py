import argparse
import json
from pathlib import Path
from checkpoint import save
from state import read_state, update

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--steps", type=int)
    args = parser.parse_args()
    target = args.directory / "state.json"
    source = args.directory / "events.jsonl"
    state = read_state(target)
    start = 0
    with source.open(encoding="utf-8") as events:
        for index, line in enumerate(events):
            if index < start:
                continue
            if args.steps is not None and index - start >= args.steps:
                return 75
            update(state, json.loads(line))
            save(target, state)
    save(target, state)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
