def read(records, key):
    value = records.get(key)
    if value is None or value == "offline":
        return None
    return value[0]
