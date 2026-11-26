def unique(messages):
    seen = set()
    for message in messages:
        key = message["id"]
        if key not in seen:
            seen.add(key)
            yield message
