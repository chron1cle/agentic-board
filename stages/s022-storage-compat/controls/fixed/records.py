import json
from pathlib import Path
import sys

def read(data):
    if type(data) is not dict:
        raise ValueError
    if data.keys() == {"entries"} and type(data["entries"]) is list:
        accounts = {}
        for e in data["entries"]:
            if type(e) is not dict or e.keys() != {"account", "cents"}:
                raise ValueError
            if type(e["account"]) is not str or type(e["cents"]) is not int:
                raise ValueError
            accounts.setdefault(e["account"], []).append(e["cents"])
        return accounts, False
    if data.keys() == {"version", "accounts"} and type(data["version"]) is int and data["version"] == 2:
        accounts = data["accounts"]
        if type(accounts) is dict and all(type(v) is list and all(type(n) is int for n in v) for v in accounts.values()):
            return accounts, True
    raise ValueError

def main():
    command, filename, *args = sys.argv[1:]
    path = Path(filename)
    accounts, current = read(json.loads(path.read_text(encoding="utf-8")))
    if command == "total" and len(args) == 1:
        print(sum(accounts.get(args[0], [])))
    elif command == "translate" and not args:
        if not current:
            path.write_text(json.dumps({"version": 2, "accounts": accounts}), encoding="utf-8")
        print("current" if current else "migrated")
    else:
        raise ValueError

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError):
        sys.exit(2)
