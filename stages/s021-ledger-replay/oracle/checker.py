from support import batch, rng

random = rng()
cases = [("empty-ledger", [], {"balances": {}, "conflicts": []})]
for i in range(20):
    base = [{"id": f"e{n}", "account": f"a{n % 4}", "seq": n,
             "delta": random.randint(-50, 50)} for n in range(14)]
    bad = set(random.sample(range(14), i % 6))
    events = base + [dict(e) for e in base[::2]]
    events += [dict(base[n], seq=100 + n) for n in bad]
    expected = {f"a{n}": 0 for n in range(4)}
    for n in set(range(14)) - bad:
        expected[base[n]["account"]] += base[n]["delta"]
    expected = {a: v for a, v in expected.items() if any(base[n]["account"] == a for n in set(range(14)) - bad)}
    for repeat in range(2):
        random.shuffle(events)
        cases.append((f"dedupe-and-order-{i}-{repeat}", events[:],
                      {"balances": expected, "conflicts": sorted(base[n]["id"] for n in bad)}))
batch("ledger.py", cases)
