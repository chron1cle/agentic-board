from support import batch, rng


def plans(device, real_moves):
    def visit(paths):
        if all(device["safe"][s] and device["labels"][s]==device["labels"][paths[0][0]] for s,e,w in paths):
            return max(w for s,e,w in paths), []
        candidates = []
        for j in range(len(real_moves[0])):
            successors = [[] for _ in range(device["signals"])]
            for s, used, spent in paths:
                options = real_moves[s][j]
                if not options or any(spent+c > device["cap"] for _,_,c in options):
                    break
                for obs, target, cost in options:
                    for seen, branch in enumerate(successors):
                        errors = used + (obs != seen)
                        if errors <= device["errors"]:
                            branch.append((target,errors,spent+cost))
            else:
                worst = max(visit(sorted(set(branch)))[0] for branch in successors if branch)
                candidates.append((worst,j))
        best = min((v for v,j in candidates),default=device["cap"]+1)
        return best,[j for v,j in candidates if v==best]

    out = []
    for start in device["starts"]:
        cost,first = visit([(s,0,0) for s in start])
        out.append(dict(credit=cost,probes=first) if cost<=device["cap"] else None)
    return out


random = rng()
cases = []
for trial in range(30):
    p = 7
    versions, pairs, values = [], [], []
    for i in range(9):
        # Branches fix sensor 0 with a self equation, then connect sensor 1.
        fixed = random.randrange(p)
        versions.append([0,["link","pin",0,0,2,-fixed%p]])
        a, b = random.randrange(1,p), random.randrange(p)
        versions.append([len(versions),["link","read",0,1,a,b]])
        branch = len(versions)
        for x, expected in [(fixed,(a*fixed+b)%p),((fixed+1)%p,"conflict")]:
            pairs.append([branch,0,1,x]); values.append(expected)
        versions.append([branch,["cut","read"]])
        pairs.append([len(versions),0,1,fixed]); values.append("separate")
    wiring = dict(n=2, p=p, versions=versions, queries=pairs)
    valid = [k for k,y in enumerate(values) if isinstance(y,int)]
    bad = [k for k,y in enumerate(values) if isinstance(y,str)]
    mapped, real, disabled = [], [], []
    for s in range(4):
        row, actual = [], []
        for j in range(3):
            picks = [(random.choice(valid),s%2+2,random.randint(1,2))]
            if j == 0:
                picks.append((random.choice(bad),s,1))
            elif j == 1 and trial%4==0:
                picks = []
            elif j == 1 and trial%3==0:
                picks.append((random.choice(valid),s,1))
            row.append(picks)
            if not picks or any(index in bad for index,_,_ in picks):
                disabled.append([s,j]); actual.append([])
            else:
                actual.append([(values[q]%2,dest,c+(values[q]//2)%3) for q,dest,c in picks])
        mapped.append(row); real.append(actual)
    device = dict(labels=[0,1,0,1],safe=[False,False,True,True],signals=2,errors=trial%2,cap=8,
                  moves=mapped,starts=[[0,1],[0,2],[0],[2,3],[3]])
    cases.append((f"commission-{trial}",dict(wiring=wiring,device=device),
                  dict(unavailable=disabled,plans=plans(device,real))))
batch("station.py",cases)
