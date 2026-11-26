from intake import unique
from dispatch import deliver

class Gateway:
    def __init__(self, responses):
        self.responses = responses
        self.counts = {}
        self.calls = []

    def send(self, key):
        self.calls.append(key)
        position = self.counts.get(key, 0)
        self.counts[key] = position + 1
        responses = self.responses.get(key, [])
        return responses[position] if position < len(responses) else "ok"

def answer(request):
    gateway = Gateway(request["responses"])
    delivered = []
    undelivered = []
    totals = {}
    for message in unique(request["messages"]):
        key = message["id"]
        result = deliver(message, gateway, request["max_attempts"])
        if result == "ok":
            delivered.append(key)
            customer = message["customer"]
            totals[customer] = totals.get(customer, 0) + message["amount"]
        else:
            undelivered.append({"id": key, "reason": "rejected" if result == "reject" else "exhausted"})
    return {"delivered": delivered, "undelivered": undelivered, "totals": totals,
            "calls": gateway.calls}


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))
