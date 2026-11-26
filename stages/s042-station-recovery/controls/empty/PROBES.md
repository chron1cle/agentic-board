Implement probe.py as a standard-library JSON Lines program. Each line is an
independent request. Return one JSON array of diagnosis results per line.

labels[i] identifies the permanent fault class of hidden state i. safe[i]
is true if the device can stop there. moves[i][j] lists the possible
[actualSignal,nextState,charge] outcomes of probe j. Outcomes are adversarial.
An empty list means this probe is unavailable in this state. Charge is a
positive integer. A probe is legal only if available for every possible
current state. It spends the charge of the actual outcome on that path.

The tester sees only the reported signal. Neither the actual state nor cost
is observed. signals is the number of different public signals 0..signals-1.
At most errors times over an entire path, the reported signal may be replaced
by ANY other signal. Whether a reading was corrupted is also hidden. The
tester may condition its next probe on all reported observations. Starts
are listed in starts (a list of nonempty sets of hidden states). Each path
starts with the same credit and a fresh error allowance.

You may stop only if all possible current states have the same label AND
are safe to stop in. Find the least initial credit from 0 through cap that
guarantees stopping without going into debt on any path. Report null if
there is none. Otherwise return {"credit":n,"probes":[...]} with ALL first
probes that win at that minimum credit in ascending index order. Already
finished means zero credit and no probes. Hidden states may merge after an
observation with different spent credit or remaining error allowance.
A single path may spend heavily on one step and cheaply on another.

At most 14 states, 5 probes, 3 signals, 2 errors, cap <= 18. All transitions
preserve fault class. Use the standard library only.

The grader runs the submitted program on a batch of requests with a
20-second runtime limit, 768 MiB of address space and 32 MiB of output.
