Implement plan.py using only the standard library. Read one independent JSON
object per stdin line and output one JSON object per line.

Select a subset of items (unique string id, positive integer cost and space,
signed integer value). Total cost and space cannot exceed budget and capacity.
requires contains directed pairs [a,b]: selecting a requires b. incompatible
contains pairs that cannot both be selected. Each bonuses triple [a,b,amount]
adds its signed amount exactly once if both endpoints are selected.

Maximize total value including bonuses, then minimize cost, then minimize
space. Among ALL subsets tied on those three criteria output:
{"value":v,"cost":c,"space":s,"ways":w,"ids":[...],"required":[...]}.
ways counts distinct tied subsets modulo 1000000007. ids is the lexicographically
smallest sorted id list among them. required is the sorted intersection of
all tied subsets. The empty subset counts once when optimal.

The request supplies a tree decomposition in bags: bag i is [parent,[ids...]]
with root parent -1, and each later parent is a lower index. Each item
appears in at least one bag and all bags containing it form a connected
subtree. Some bags may be empty or identical. Every pair mentioned in a rule
appears together in at least one bag. Bags may overlap and sibling subtrees
share assignments on their common items. An item, rule, or subset counts
only once, regardless of how many bags contain it.

Up to 100 items, 180 bags, five ids per bag and budgets up to 60. Full subset
enumeration may not finish. All limits apply per input line.

The grader runs the submitted program on a batch of requests with a
20-second runtime limit, 768 MiB of address space and 32 MiB of output.
