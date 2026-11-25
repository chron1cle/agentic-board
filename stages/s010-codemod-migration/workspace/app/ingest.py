"""Bulk ingest of raw records onto the bus."""

from messenger.legacy import Bus
from settings import bus_settings


def ingest(records):
    """Publish every record, return how many the bus took."""
    cfg = bus_settings()
    bus = Bus(cfg["host"], cfg["port"], cfg["timeout"])
    taken = 0
    for record in records:
        if bus.send("ingest.record", record):
            taken += 1
    bus.close()
    return taken
