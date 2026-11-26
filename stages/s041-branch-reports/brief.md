Implement report.py with only the standard library. Read one independent
JSON object per stdin line and write one array per line. A ledger has D days,
numbered 0 through D-1, given in days. Version 0 has no rows and all account
rates default to 1. versions[i-1] is [parent, edit], creating version i from
any lower numbered version. All changes are local to that branch.

["post",id,account,day,units] inserts or replaces the entire row for id.
["drop",id] removes it (a missing id is harmless). ["rate",account,r] replaces
that account's rate, revaluing every active row for that account. Units and
rates may be positive, zero, or negative integers. Account and row ids are
strings. A replacement may change its account, day and units at once.

For each query [version,lo,hi] return [count,total] for active rows in the
inclusive day range. Every active row counts, including rows with zero units
or zero rate. Each contributes units times its account's rate in that
version. Return answers in query order. 0 <= lo <= hi < D.

Example: versions [[0,["post","f","A",1,3]],[1,["rate","A",-2]],
[1,["post","f","B",0,4]]] and queries [[2,0,1],[3,0,1],[1,0,1]]
with days=2 yield [[1,-6],[1,4],[1,3]].

There may be 40,000 versions, days and queries each. Both the depth and width
of the history can be large. A single account may have many rows spread over
many days, and there may also be many accounts with few rows. Avoid copying
a complete ledger at every fork or scanning all rows for each report.

The grader runs the submitted program on a batch of requests with a
20-second runtime limit, 768 MiB of address space and 32 MiB of output.
