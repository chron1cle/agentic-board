#!/usr/bin/env python3
"""Behavioural checks against the migrated app layer."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": bool(ok), "detail": detail,
                      "evidence": str(evidence)[:800]}))


class Flaky:
    """Publishes fine after `fails` failures. Records everything."""

    def __init__(self, fails=0):
        from messenger.v2 import DeliveryError
        self._error = DeliveryError
        self.fails = fails
        self.published = []
        self.attempts = 0
        self.closed = False

    def publish(self, event):
        self.attempts += 1
        if self.fails > 0:
            self.fails -= 1
            raise self._error("broker down")
        self.published.append(event)

    def close(self):
        self.closed = True


def main():
    try:
        from app.billing import charge
        from app.ingest import ingest
        from app.notifier import notify
        from app.retry import with_retry
        from messenger.v2 import Client, DeliveryError, Event
    except Exception as exc:
        emit("imports", False, f"app does not import: {exc}")
        return 0
    emit("imports", True)

    client = Flaky()
    try:
        result = notify("u1", "hello", client=client)
        event = client.published[0] if client.published else None
        emit("notify-publishes-event",
             result is True and event is not None and event.kind == "user.notify"
             and event.body == {"user": "u1", "text": "hello"} and event.key == "u1",
             f"got {event!r}")
    except Exception as exc:
        emit("notify-publishes-event", False, f"raised {exc!r}")
    emit("caller-owned-client-not-closed", not client.closed,
         "the passed-in client was closed by the function")

    try:
        notify("u2", "x")
        emit("default-client-from-config", True)
    except Exception as exc:
        emit("default-client-from-config", False, f"notify() with no client raised {exc!r}")

    client = Flaky(fails=2)
    try:
        result = charge("u9", 1250, client=client)
        event = client.published[0] if client.published else None
        emit("charge-retries-then-succeeds",
             client.attempts == 3 and event is not None
             and event.kind == "billing.charge"
             and event.body == {"user": "u9", "cents": 1250} and event.key == "u9",
             f"attempts={client.attempts} event={event!r}")
    except Exception as exc:
        emit("charge-retries-then-succeeds", False, f"raised {exc!r} after {client.attempts} attempts")

    client = Flaky(fails=99)
    try:
        charge("u9", 100, client=client)
        emit("charge-propagates-error", False, "DeliveryError did not reach the caller")
    except DeliveryError:
        emit("charge-propagates-error", client.attempts == 3,
             f"raised after {client.attempts} attempt(s), expected 3")
    except Exception as exc:
        emit("charge-propagates-error", False, f"wrong exception {exc!r}")

    client = Flaky()
    try:
        taken = ingest([{"a": 1}, {"a": 2}, {"a": 3}], client=client)
        kinds = [e.kind for e in client.published]
        bodies = [e.body for e in client.published]
        emit("ingest-publishes-all",
             taken == 3 and kinds == ["ingest.record"] * 3
             and bodies == [{"a": 1}, {"a": 2}, {"a": 3}],
             f"returned {taken!r} kinds={kinds}")
    except Exception as exc:
        emit("ingest-publishes-all", False, f"raised {exc!r}")

    try:
        ingest([{"a": 1}], client=Flaky(fails=99))
        emit("ingest-propagates-error", False, "DeliveryError did not reach the caller")
    except DeliveryError:
        emit("ingest-propagates-error", True)
    except Exception as exc:
        emit("ingest-propagates-error", False, f"wrong exception {exc!r}")

    emit("retry-returns-value", with_retry(lambda: "v") == "v")
    counter = {"n": 0}

    def always_bad():
        counter["n"] += 1
        raise DeliveryError("no")

    try:
        with_retry(always_bad, attempts=3)
        emit("retry-reraises", False, "no exception after exhausting attempts")
    except DeliveryError:
        emit("retry-reraises", counter["n"] == 3, f"called {counter['n']} times, expected 3")

    try:
        client_obj = Client()
        emit("client-reads-config",
             client_obj.config.get("broker_port") == 5672
             and client_obj.config.get("timeout_ms") == 2500,
             f"config={client_obj.config}")
    except Exception as exc:
        emit("client-reads-config", False, f"Client() raised {exc!r}")

    try:
        with Client() as ctx:
            ctx.publish(Event("t", {}))
        emit("client-context-manager", ctx._closed, "client not closed on exit")
    except Exception as exc:
        emit("client-context-manager", False, f"raised {exc!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
