#!/usr/bin/env python3
"""Config migration checks."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def emit(name, ok, detail="", evidence=""):
    print(json.dumps({"check": name, "pass": bool(ok), "detail": detail,
                      "evidence": str(evidence)[:800]}))


def main():
    ini = Path("settings.ini")
    emit("ini-removed", not ini.exists(),
         "settings.ini is gone" if not ini.exists() else "settings.ini still present")

    path = Path("config.yaml")
    if not path.exists():
        emit("config-yaml", False, "config.yaml is missing")
        return 0
    try:
        import yaml
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:
        emit("config-yaml", False, f"config.yaml does not parse: {exc}")
        return 0
    broker = data.get("broker", {})
    app = data.get("app", {})
    problems = []
    if broker.get("host") != "10.0.0.4":
        problems.append(f"broker.host is {broker.get('host')!r}")
    if int(broker.get("port", -1)) != 5672:
        problems.append(f"broker.port is {broker.get('port')!r}")
    if int(broker.get("timeout_ms", -1)) != 2500:
        problems.append(f"broker.timeout_ms is {broker.get('timeout_ms')!r} (2.5s = 2500ms)")
    if app.get("name") != "ledger" or app.get("region") != "eu-west-1":
        problems.append(f"app section is {app!r}")
    emit("config-yaml", not problems, "config.yaml carries the migrated values",
         "; ".join(problems))

    try:
        import settings
        got = settings.bus_settings()
    except Exception as exc:
        emit("settings-api", False, f"settings.bus_settings() failed: {exc}")
        return 0
    want = {"broker_host": "10.0.0.4", "broker_port": 5672, "timeout_ms": 2500}
    emit("settings-api", got == want, f"got {got}", f"want {want}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
