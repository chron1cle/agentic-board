# The Reset Relay

**Summit routing 4/10** · This level adds `clear`.

Implement `route.py` using the Python standard library. It reads one JSON object
per line from stdin until EOF and writes one JSON integer per line giving the
minimum total route cost, or JSON `null` when the goal is unreachable.

Each input has integer `nodes` (1–40), `switches` (0–4), `start` and `goal`,
and an `edges` array of at most 240 directed edges. An edge has integers `u` and
`v` (node indices), and `cost` (0–100). Both node and switch indices start at
zero. Switches start off. Self-loops, parallel edges, zero-cost edges, and
revisits are allowed. An optional top-level `arrival_on` array lists distinct
switch indices that must be on when the route ends. All other switches can have
either value unless otherwise constrained. You may leave the goal and return
later. Starting at the goal costs zero if the initial state satisfies the goal.

Optional edge fields may appear together. Missing fields have no effect.

| Field | Value | Rule |
| --- | --- | --- |
| `toggle` | one switch index | Flip the indicated switch after crossing. |
| `need_on` | one switch index | Allow the edge only when the indicated switch is on. |
| `need_off` | one switch index | Allow the edge only when the indicated switch is off. |
| `clear` | one switch index | Set the indicated switch to off after crossing. |

Check any gates against the incoming switch state. Then apply edge effects in
this order: `toggle`, `clear`. Each effect sees the state after any previous
effect. Indices are valid. All inputs are well formed.

For example, this input returns `5`.

```json
{"nodes":2,"switches":1,"start":0,"goal":1,"edges":[{"u":0,"v":1,"cost":5,"toggle":0}]}
```
