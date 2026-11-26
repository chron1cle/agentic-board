Commission a diagnostic station. The wiring service network.py must implement
NETWORK.md and the policy service probe.py must implement PROBES.md. Both
services are independently exercised at their documented scale. Also build
station.py to connect them. All three are standard-library JSON Lines CLIs.

A station request is {"wiring": ..., "device": ...}. wiring has the exact
network.py input format, including queries. device has the probe.py format
except that each possible transition is [queryIndex,nextState,baseCharge].
The indexed wiring query is a calibration measurement. For an integer
reading y, the transition's actual signal is y modulo signals, and its
actual charge is baseCharge + ((y div signals) modulo 3), with integer
division. Neither signal corruption nor charge is resolved until the
diagnosis runs. Budgets, safety and optimal first probes follow PROBES.md.

If any possible transition of a state/probe has a measurement "separate" or
"conflict", disable that entire probe in that state. An initially empty list
of transitions is also disabled. A reading of integer zero is valid.
Return {"unavailable":[[state,probe],...],"plans":[...]} with unavailable
pairs sorted by state then probe and plans in device.starts order.
Each request is independent. The same query or physical link may be used by
several devices or transitions, with different base charges. The integrated
CLI has the same batch resource limits as the services.
