Implement schedule.py. Each stdin line is a separate JSON object with workers
(the initial capacity), jobs, cancels, and shifts. Print one JSON event array
per input line using only the Python standard library.

Each job has a unique string id, release time, positive duration in running
ticks, priority (larger first), crew (workers required together), and deps
(an acyclic list of prerequisite ids). Each shift [time,capacity] changes
capacity from that tick onward. Shift times are unique. Cancellations are
[time,id]. Input lists are unordered. Times and durations are nonnegative
integers up to one billion. The final capacity can accommodate any job.

At time t, account for work during [previous time,t) first. Then:
1. Cancel each requested unfinished job, including any due to finish now,
   and all its unfinished descendants. Ignore requests for already terminal
   jobs. Emit one [t,"cancel",id] per affected job in id order.
2. Finish surviving jobs whose remaining duration reached zero. Emit
   [t,"finish",id] in id order. Their dependents can run immediately.
3. Apply the shift at t, if any. Rebuild the running set from all released,
   unfinished jobs with finished prerequisites, including jobs already running.
   Scan by descending priority, then ascending id. Select each job if its
   whole crew still fits, skipping oversized jobs and continuing the scan.
4. Emit [t,"pause",id] in id order for formerly running, nonterminal jobs
   left out. Emit [t,"start",id] or [t,"resume",id] in selection order for
   newly running jobs. A previously started job retains its remaining work.
   Continuing jobs emit nothing.

A running job consumes one duration tick per elapsed tick regardless of crew
size. Emit no idle events. Gaps between events may be long.
