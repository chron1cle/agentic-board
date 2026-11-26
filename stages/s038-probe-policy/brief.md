Build probe.py, a planner for testing a black-box device whose hidden state
can change during a probe. Use only the standard library. Each input line is
an independent JSON object. Write one JSON array per line.

labels[i] is the fault class of hidden state i. costs[j] is the positive
integer cost of probe j. moves[i][j] lists possible [signal,nextState]
outcomes, all chosen adversarially. An empty list means probe j is unsafe
in state i. Several actual outcomes can give the same public signal. The
diagnostician observes only signals and its own probes. Next states always
have the same class as their source. starts lists sets of possible initial
states, one diagnosis per set.

Stop once all still-possible states have the same class. A strategy may
choose its next safe probe based on every signal seen so far. It must stop
after finitely many probes on every possible path. Minimize the worst-case
sum of probe costs. For each start set return {"cost":c,"probes":[...]}
listing ALL possible first probe indices of optimal strategies, ascending.
An already diagnosed set gives cost zero and an empty list. If a diagnosis
cannot be guaranteed, return null. A cycle that can continue forever loses
even if some outcomes leave it. A probe with one signal may still change
the hidden state and enable a later diagnosis.

Inputs have at most 20 states, 6 probes, and 4 distinct integer signals.
At most 2,000 distinct sets of possible states are reachable per request.

The grader runs the submitted program on a batch of requests with a
20-second runtime limit, 768 MiB of address space and 32 MiB of output.
