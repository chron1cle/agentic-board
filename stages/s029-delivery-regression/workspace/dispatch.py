def deliver(message, gateway, max_attempts):
    for _ in range(max_attempts + 1):
        if gateway.send(message['id']) == 'ok':
            return 'ok'
    return 'retry'
