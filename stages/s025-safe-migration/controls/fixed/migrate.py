import argparse
import json
import os
from pathlib import Path
import tempfile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--interrupt", type=int)
    args = parser.parse_args()
    directory = args.directory
    records = json.loads((directory / "legacy.json").read_text(encoding="utf-8"))
    with tempfile.NamedTemporaryFile(dir=directory, delete=False, mode="w", encoding="utf-8") as output:
        path = Path(output.name)
        for index, name in enumerate(sorted(records)):
            if index == args.interrupt:
                return 75
            output.write(json.dumps({"name": name, "value": records[name]}, separators=(",", ":")) + "\n")
        if args.interrupt == len(records):
            return 75
        output.flush()
        os.fsync(output.fileno())
    os.replace(path, directory / "current.jsonl")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
