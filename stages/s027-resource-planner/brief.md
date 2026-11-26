Implement plan.py as JSON Lines. Input has budget (integer >= 0), items (at
most 25 objects), and incompatible (pairs of item ids). Each item has a
unique string id, positive integer cost, nonnegative integer value, and a list
of prerequisite ids in requires. Requirements form an acyclic graph.

Choose a subset with total cost <= budget, containing every chosen item's
prerequisites, and containing no incompatible pair. Maximize total value,
then minimize total cost, then choose the lexicographically smallest sorted
list of selected ids. Output {"ids":[...], "cost":integer, "value":integer}.
The empty selection is valid. Standard library only. Avoid enumerating all
subsets when a branch cannot improve the answer.
