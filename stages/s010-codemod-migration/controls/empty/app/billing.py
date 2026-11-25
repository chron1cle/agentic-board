"""Charge a customer through the bus."""

from app.retry import with_retry
from messenger.legacy import Bus
from settings import bus_settings


def charge(user_id, cents):
    cfg = bus_settings()
    bus = Bus(cfg["host"], cfg["port"], cfg["timeout"])
    try:
        return with_retry(lambda: bus.send("billing.charge",
                                            {"user": user_id, "cents": cents}))
    finally:
        bus.close()
