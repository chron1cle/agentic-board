def deliver(message, gateway, max_attempts):
    for _ in range(max_attempts):
        outcome = gateway.send(message["id"])
        if outcome != "retry":
            return outcome
    return "retry"
