import json
import sys
from network import solve as readings
from probe import solve as diagnose


def commission(case):
    values = readings(case["wiring"])
    device = case["device"]
    signals = device["signals"]
    moves, unavailable = [], []
    for i, row in enumerate(device["moves"]):
        compiled = []
        for j, transitions in enumerate(row):
            options = []
            for index, following, base in transitions:
                y = values[index]
                if not isinstance(y, int):
                    options = []
                    break
                options.append([y % signals, following, base+(y//signals)%3])
            if not options:
                unavailable.append([i,j])
            compiled.append(options)
        moves.append(compiled)
    return dict(unavailable=unavailable, plans=diagnose(dict(device,moves=moves)))


for line in sys.stdin:
    print(json.dumps(commission(json.loads(line))))
