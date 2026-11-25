"""DEPRECATED v1 bus. Kept only so the migration can be diffed; nothing may
import this after the migration is done."""

import warnings


class Bus:
    def __init__(self, host, port, timeout=2.5):
        warnings.warn("messenger.legacy is deprecated, move to messenger.v2",
                      DeprecationWarning, stacklevel=2)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sent = []
        self._closed = False

    def send(self, kind, payload):
        """Return True when handed off, False when not. No exceptions, ever."""
        if self._closed:
            return False
        self.sent.append((kind, payload))
        return True

    def close(self):
        self._closed = True
