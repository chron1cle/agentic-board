import json

def read_state(path):
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if "offset" not in data:
            return {"version": 2, "offset": data["cursor"], "items": data["items"],
                    "totals": totals(data["items"])}
        return data
    return {"version": 2, "offset": 0, "items": {}, "totals": {}}

def totals(items):
    result = {}
    for event in items.values():
        if event["amount"] is not None:
            account = event["account"]
            result[account] = result.get(account, 0) + event["amount"]
    return result

def update(state, event):
    key = event["id"]
    existing = state["items"].get(key)
    if existing is None or event["revision"] > existing["revision"]:
        state["items"][key] = {name: event[name] for name in ("revision", "account", "amount")}
    state["offset"] += 1
    state["totals"] = totals(state["items"])
