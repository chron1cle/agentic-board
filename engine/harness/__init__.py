"""Harness registry. Add an adapter here to make it selectable from the CLI."""

from __future__ import annotations

from .adapters import (AntigravityAdapter, ClineAdapter, CodexAdapter, CommandAdapter,
                       GrokBuildAdapter, HermesAdapter, KiloAdapter, PiAdapter)
from .t3code import T3CodeAdapter
from .base import HarnessAdapter, HarnessRequest, HarnessResult
from .fake import FakeHarness
from .opencode import OpenCodeAdapter, resolve_default_model
from .solve import SolveHarness

REGISTRY: dict[str, type[HarnessAdapter]] = {
    "opencode": OpenCodeAdapter,
    "cline": ClineAdapter,
    "kilo": KiloAdapter,
    "codex": CodexAdapter,
    "grokbuild": GrokBuildAdapter,
    "antigravity": AntigravityAdapter,
    "t3code": T3CodeAdapter,
    "hermes": HermesAdapter,
    "pi": PiAdapter,
    "command": CommandAdapter,
    "fake": FakeHarness,
    "solve": SolveHarness,
}


def available_harnesses() -> dict[str, tuple[bool, str]]:
    return {name: cls().available() for name, cls in REGISTRY.items()}


def create(name: str, model: str | None = None, **kwargs) -> HarnessAdapter:
    if name not in REGISTRY:
        raise ValueError(f"unknown harness {name!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[name](model=model, **kwargs)


__all__ = ["REGISTRY", "HarnessAdapter", "HarnessRequest", "HarnessResult",
           "FakeHarness", "OpenCodeAdapter", "SolveHarness",
           "available_harnesses", "create", "resolve_default_model"]
