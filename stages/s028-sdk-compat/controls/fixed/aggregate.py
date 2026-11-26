from reader import collect

def report(sensor, keys):
    rows = [collect(sensor, key) for key in keys]
    return {"rows": rows, "total_milli": sum(row.get("milli", 0) for row in rows),
            "calls": sensor.calls}
