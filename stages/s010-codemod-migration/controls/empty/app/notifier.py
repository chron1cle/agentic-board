"""Push user-visible notifications."""

from messenger.legacy import Bus
from settings import bus_settings

_bus = None


def _bus_instance():
    global _bus
    if _bus is None:
        cfg = bus_settings()
        _bus = Bus(cfg["host"], cfg["port"], cfg["timeout"])
    return _bus


def notify(user_id, message):
    """Tell a user something. Returns True if the bus took it."""
    return _bus_instance().send("user.notify", {"user": user_id, "text": message})
