from reader import collect
def report(sensor, keys):
    return sum(collect(sensor, key) or 0 for key in keys)
