import argparse
import json
import os
from pathlib import Path
import tempfile


def migrate(root, interrupt):
    rows = json.loads((root / "legacy.json").read_text())
    plan = root / "batches.json"
    for pairs in json.loads(plan.read_text()) if plan.exists() else []:
        sources = {a for a, b in pairs}
        targets = {b for a, b in pairs}
        if (len(pairs) != len(sources) or len(pairs) != len(targets) or
                not sources <= rows.keys() or targets & (rows.keys() - sources)):
            return 2
        moved = {b: rows[a] for a, b in pairs}
        for a in sources:
            del rows[a]
        rows.update(moved)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False, encoding="utf-8") as output:
            temp_path = Path(output.name)
            for i, name in enumerate(sorted(rows)):
                if i == interrupt:
                    return 75
                print(json.dumps(dict(name=name, value=rows[name]), separators=(",", ":")), file=output)
            if len(rows) == interrupt:
                return 75
        os.replace(temp_path, root / "current.jsonl")
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)
    return 0


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--interrupt", type=int)
args = parser.parse_args()
raise SystemExit(migrate(args.directory, args.interrupt))
