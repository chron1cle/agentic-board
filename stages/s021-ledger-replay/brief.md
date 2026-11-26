Implement ledger.py as a JSON Lines program. Each input is an array of event
objects with string id, string account, integer seq, and integer delta.
Output {"balances": {...}, "conflicts": [...]}.

Group events by id. Exact repeats count once. If an id has two or more distinct
(account, seq, delta) triples, discard every copy of that id and list its id once
in conflicts, sorted lexicographically. For the remaining events, sum deltas by
account. Accounts with an accepted event stay in balances even at zero. The
result must be invariant under rearranging the events. Empty input gives empty
balances and conflicts. Each line is a separate ledger. Standard library only.
