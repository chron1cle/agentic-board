Implement network.py. Read independent JSON objects, one per stdin line,
and write one JSON array per line using only the standard library.

There are n sensors (0-based) whose readings are integers modulo prime p.
Version 0 contains no links. Entry versions[i-1] = [parent,edit] builds
version i from an earlier version. A ["link",id,u,v,a,b] constrains
reading[v] = a*reading[u]+b modulo p, with 1 <= a < p and 0 <= b < p.
["cut",id] removes a live link and ["noop"] does nothing. Link ids are
strings and may be reused after removal. Edits affect only their branch.
Parallel and self links are legal. A cycle can fix one reading to a unique
value, impose no new constraint, or contradict existing constraints.

Each query [version,u,v,x] provisionally pins reading[u] to x. First reply
"separate" if u and v belong to different connected components. Otherwise
reply "conflict" if the equations in their component, including the pin,
have no solution. Otherwise reply with the implied integer reading at v in
0..p-1. Pins never persist. Ignore contradictions in other components.
Answers follow query order.

For example, with p=5, a self link reading[0]=2*reading[0]+1 permits only
reading[0]=4. Connecting it to reading[1]=3*reading[0]+2 gives reading[1]=4.
A query pinning sensor 1 to 0 now conflicts. Cutting the self link restores
a free choice of the anchored reading.

p is at most 1009. There can be 40,000 versions, sensors, and queries each.
Versions can be long chains with many sibling branches. Avoid reconstructing
all constraints of a version per query or keeping a whole graph per version.

The grader runs the submitted program on a batch of requests with a
20-second runtime limit, 768 MiB of address space and 32 MiB of output.
