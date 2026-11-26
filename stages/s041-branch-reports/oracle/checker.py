from support import batch, rng

random = rng()
cases = []
for trial in range(30):
    edits, states, queries, answers = [], [({}, {})], [], []
    for i in range(1,100):
        parent = i-1 if random.random()<0.65 else random.randrange(i)
        previous, weights = states[parent]
        rows, rates = previous.copy(), weights.copy()
        key, account = str(random.randrange(9)), str(random.randrange(7))
        op = random.choice(["post","post","post","drop","rate"])
        if op == "post":
            day, units = random.randrange(11), random.randint(-5,5)
            rows[key] = (account,day,units)
            edit = [op,key,account,day,units]
        elif op == "drop":
            rows.pop(key,None)
            edit = [op,key]
        else:
            r = random.randint(-3,3)
            rates[account] = r
            edit = [op,account,r]
        states.append((rows,rates))
        edits.append([parent,edit])
    for _ in range(500):
        node = random.randrange(len(states))
        lo,hi = sorted([random.randrange(11),random.randrange(11)])
        rows,rates = states[node]
        values = [units*rates.get(a,1) for a,d,units in rows.values() if lo<=d<=hi]
        queries.append([node,lo,hi])
        answers.append([len(values),sum(values)])
    cases.append((f"historical-joins-{trial}",dict(days=11,versions=edits,queries=queries),answers))

days = 7800
edits, queries, answers = [], [], []
big, small = [0], [0]
for d in range(days):
    v,w = random.randrange(-30,31),random.randrange(-30,31)
    big.append(big[-1]+v)
    small.append(small[-1]+w)
    edits.append([len(edits),["post",f"h{d}","common",d,v]])
    edits.append([len(edits),["post",f"l{d}",f"a{d}",d,w]])
base = len(edits)
for i in range(days):
    rate = random.randint(-20,20)
    edits.append([base,["rate","common",rate]])
    parent = len(edits)
    key = random.randrange(days)
    other = random.randint(-10,10)
    edits.append([parent,["rate",f"a{key}",other]])
    for version,r,rr in ((parent,rate,1),(len(edits),rate,other),(base,1,1)):
        lo,hi = sorted([random.randrange(days),random.randrange(days)])
        delta = (other-1)*(small[key+1]-small[key]) if rr!=1 and lo<=key<=hi else 0
        total = (big[hi+1]-big[lo])*r + small[hi+1]-small[lo]+delta
        queries.append([version,lo,hi])
        answers.append([2*(hi-lo+1),total])
order = random.sample(range(len(queries)),len(queries))
cases.append(("forked-account-revaluations",dict(days=days,versions=edits,queries=[queries[i] for i in order]),
              [answers[i] for i in order]))
batch("report.py",cases)
