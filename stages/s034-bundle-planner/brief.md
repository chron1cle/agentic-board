Implement plan.py with Python's standard library. Each input line is one
independent JSON object. Write one JSON object per line.

items have a unique string id, positive integer cost and space, nonnegative
integer value, and requires (prerequisite ids forming an acyclic graph).
budget and capacity limit total cost and space respectively. incompatible
lists pairs of ids that cannot coexist. bonuses contains [a,b,points] triples
with distinct endpoints and signed integer points. Each triple contributes
its points once if both items are selected. Every selected item must have all
its prerequisites selected. The empty plan is legal.

Maximize value including bonuses, then minimize cost, then minimize space,
then choose the lexicographically smallest sorted list of selected ids.
Return {"ids":[...],"value":integer,"cost":integer,"space":integer}.

There can be 48 items. Linking ids mentioned together by any prerequisite,
incompatibility, or bonus gives independent groups of at most eight items.
Groups still share the two budgets (each 0 through 60). Input order has no
meaning. For example, two items worth 3 and 4 with a -6 bonus are worth 1
together, even when both fit.
