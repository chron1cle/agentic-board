from sensor_v2 import Missing, Unavailable

def collect(sensor, key):
    try:
        reading = sensor.fetch(key)
    except Missing:
        return {"id": key, "status": "missing"}
    except Unavailable:
        return {"id": key, "status": "offline"}
    if reading.unit == "milli":
        return {"id": key, "status": "ok", "milli": reading.value}
    if reading.unit == "whole":
        return {"id": key, "status": "ok", "milli": reading.value * 1000}
    return {"id": key, "status": "invalid"}
