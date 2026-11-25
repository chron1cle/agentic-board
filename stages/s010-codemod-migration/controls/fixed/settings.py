"""Application settings, read from config.yaml."""

from messenger.v2 import load_config


def bus_settings():
    data = load_config("config.yaml")
    return {"broker_host": data["broker_host"], "broker_port": data["broker_port"],
            "timeout_ms": data["timeout_ms"]}


def app_name():
    return load_config("config.yaml")["app_name"]
