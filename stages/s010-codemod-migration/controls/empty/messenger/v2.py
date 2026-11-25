"""The v2 messenger SDK. This is the target of the migration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class DeliveryError(Exception):
    """Raised when a publish could not be handed to the broker."""


@dataclass
class Event:
    kind: str
    body: dict
    key: str | None = None
    headers: dict = field(default_factory=dict)


def load_config(path="config.yaml"):
    """Read the YAML config. Missing file or keys raise immediately."""
    import yaml

    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    broker = data.get("broker", {})
    return {
        "broker_host": broker["host"],
        "broker_port": int(broker["port"]),
        "timeout_ms": int(broker["timeout_ms"]),
        "app_name": data.get("app", {}).get("name"),
        "region": data.get("app", {}).get("region"),
    }


class Client:
    """Publishes events. Failure is an exception, never a False return."""

    def __init__(self, config_path="config.yaml"):
        self.config = load_config(config_path)
        self.published: list[Event] = []
        self._closed = False

    def publish(self, event: Event) -> None:
        if self._closed:
            raise DeliveryError("client is closed")
        if not isinstance(event, Event):
            raise TypeError("publish() requires an Event")
        self.published.append(event)

    def close(self) -> None:
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
