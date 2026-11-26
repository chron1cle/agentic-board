Implement network.py as a standard-library JSON Lines program. Each line is an
independent request. Return one JSON array of answers per line.

A plant has n binary sensors numbered 0 through n-1. Version 0 has no wires.
versions[i-1] is [parent, edit] and creates version i from an earlier version.
["link",id,u,v,b] asserts that readings at u and v differ by XOR b (0 or 1).
["cut",id] removes the named wire. ["noop"] preserves the wiring. Link ids
are strings, unique while live in a version. An id removed on one branch may
be reused for a different wire. A cut always names a live wire. Parallel
wires and loops are legal. Edits never change a parent or sibling version.

For each [version,u,v] in queries, return "separate" if the sensors are in
different connected components. Otherwise, if any constraints in their
component contradict one another, return "conflict". Otherwise return their
XOR difference as 0 or 1. Return answers in query order.

For example, {"n":2,"versions":[[0,["link","x",0,1,1]],[1,["cut","x"]],
[1,["link","y",0,1,0]]],"queries":[[2,0,1],[3,0,0],[1,0,1]]} gives
["separate","conflict",1].

Up to 40,000 versions, sensors, and queries per request. Histories can be
deep and highly branched. Rebuilding the active graph for every query or
copying it in full at each version will exceed the available resources.

The grader runs the submitted program on a batch of requests with a
20-second runtime limit, 768 MiB of address space and 32 MiB of output.
