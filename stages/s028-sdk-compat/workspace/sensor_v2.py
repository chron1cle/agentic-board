from dataclasses import dataclass

class Missing(Exception):
    pass

class Unavailable(Exception):
    pass

@dataclass(frozen=True)
class Reading:
    value: int
    unit: str

class Sensor:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def fetch(self, key):
        self.calls.append(key)
        value = self.records.get(key)
        if value is None:
            raise Missing(key)
        if value == "offline":
            raise Unavailable(key)
        return Reading(value[0], value[1])
