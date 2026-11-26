import json


def read_state(path):
    raw = json.loads(path.read_bytes()) if path.exists() else {}
    if raw.get("version") == 3:
        return raw
    items = raw.get("items", {})
    return dict(version=3, offset=raw.get("offset", raw.get("cursor", 0)),
                items=items, totals=totals(items), open={}, rejected=0)


def totals(items):
    sums = {}
    for item in items.values():
        if item["amount"] is not None:
            key = item["account"]
            sums[key] = sums.get(key, 0) + item["amount"]
    return sums


def update(state, entry):
    op, tx = entry["op"], entry["tx"]
    pending = state["open"]
    if op == "begin":
        pending[tx] = []
    elif op == "write":
        pending[tx].append(entry)
    elif op == "abort":
        del pending[tx]
    else:
        staged = {}
        for row in pending.pop(tx):
            key = row["id"]
            current = staged.get(key, state["items"].get(key, {}))
            if current.get("revision", 0) != row["expect"]:
                state["rejected"] += 1
                break
            staged[key] = dict(revision=row["expect"] + 1, account=row["account"], amount=row["amount"])
        else:
            state["items"].update(staged)
            state["totals"] = totals(state["items"])
    state["offset"] += 1
