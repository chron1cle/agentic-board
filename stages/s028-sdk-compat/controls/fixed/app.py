from aggregate import report
from sensor_v2 import Sensor

def answer(request):
    return report(Sensor(request["records"]), request["keys"])


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))
