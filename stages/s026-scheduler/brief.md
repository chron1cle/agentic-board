Implement schedule.py as JSON Lines. Each input has workers (positive integer),
jobs, and cancels. Each job has a unique string id, integer release >= 0,
integer duration >= 1, integer priority, and deps, an array of dependency ids.
The dependency graph is acyclic. Each cancellation is [time,id].

Simulate integer time. At each time handle cancellations first, then finishes,
then start ready jobs. A cancellation applies to its job and all descendants
that have not finished, immediately freeing their workers. Ignore a
cancellation of a job that has already finished. If cancellation and finish
occur at the same time, cancellation wins. A ready job has reached release
time, has finished dependencies, and is neither running nor terminal. Fill
workers in priority descending, id lexicographic order. Workers are
interchangeable. Output an array of [time,"start"|"finish"|"cancel",id].
At each time simultaneous cancellations and finishes are each sorted by id.
At a finish, dependents may start in the same tick. Input times and durations
are <= 100. Standard library only.
