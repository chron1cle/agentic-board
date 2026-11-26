from support import batch, rng

random = rng()
cases = [("empty-dispatch", {"messages": [], "responses": {}, "max_attempts": 1},
          {"delivered": [], "undelivered": [], "totals": {}, "calls": []})]
for i in range(32):
    values = [random.randrange(-100, 100) for _ in range(6)]
    orders = [dict(id=str(n), customer="b" if n == 3 else "a", amount=value)
              for n, value in enumerate(values)]
    random.shuffle(orders)
    attempts = 2 + i % 3
    messages = orders + [dict(order, amount=999) for order in orders[::2]]
    outcomes = {"0": ["retry", "ok"], "1": ["reject", "ok"], "2": ["retry"] * attempts,
                "4": ["retry"], "5": ["ok", "reject"]}
    success = [order for order in orders if order["id"] not in {"1", "2"}]
    success_ids = [order["id"] for order in success]
    expected = {
        "delivered": success_ids,
        "totals": {customer: sum(order["amount"] for order in success if order["customer"] == customer)
                   for customer in {"a", "b"}},
        "undelivered": [
            {"id": order["id"], "reason": "rejected" if order["id"] == "1" else "exhausted"}
            for order in orders if order["id"] in {"1", "2"}
        ],
        "calls": [order["id"] for order in orders
                  for _ in range({"0": 2, "2": attempts, "4": 2}.get(order["id"], 1))],
    }
    cases.append((f"incident-replay-{i}", {"messages": messages, "responses": outcomes,
                  "max_attempts": attempts}, expected))
batch("app.py", cases)
