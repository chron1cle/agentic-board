"""Disposable session storage for one external benchmark attempt."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def link_files(source, destination, names):
    """Expose installed settings or login files without linking a session directory."""
    for name in names:
        original = source / name
        if original.is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(original.resolve())


@contextmanager
def attempt_environment(harness):
    source = os.environ
    home = Path.home()
    data = Path(source.get("XDG_DATA_HOME") or home / ".local/share")
    config = Path(source.get("XDG_CONFIG_HOME") or home / ".config")
    with tempfile.TemporaryDirectory(prefix="agentic-attempt-") as directory:
        root = Path(directory)
        private_home = root / "home"
        private_home.mkdir()
        (root / "runtime").mkdir(mode=0o700)
        env = {
            **source,
            "HOME": str(private_home),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_RUNTIME_DIR": str(root / "runtime"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(root / "state"),
            # Preserve installed binaries when PATH points at a mise shim.
            "MISE_DATA_DIR": str(source.get("MISE_DATA_DIR") or data / "mise"),
            "MISE_CONFIG_DIR": str(source.get("MISE_CONFIG_DIR") or config / "mise"),
            "OPENCODE_DB": ":memory:",
            "KILO_DB": str(root / "kilo.db"),
            "KILO_NO_DAEMON": "1",
            "CLINE_DIR": str(root / "cline"),
            "CLINE_DATA_DIR": str(root / "cline/data"),
            "CLINE_SANDBOX_DATA_DIR": str(root / "cline/data"),
            "CLINE_SESSION_BACKEND_MODE": "local",
            "GROK_HOME": str(root / "grok"),
            "GROK_LEADER_SOCKET": str(root / "leader.sock"),
            "HERMES_HOME": str(root / "hermes"),
            "ANTIGRAVITY_GEMINI_DIR": str(private_home / ".gemini"),
            "ANTIGRAVITY_APP_DATA_DIR": str(private_home / ".gemini/antigravity-cli"),
            "T3CODE_HOME": str(root / "t3"),
            "CLAUDE_CONFIG_DIR": str(root / "claude"),
            "CODEX_HOME": str(root / "codex"),
            "CODEX_SQLITE_HOME": str(root / "codex"),
            "PI_CODING_AGENT_DIR": str(root / "pi"),
        }
        for key in ("OPENCODE_SESSION_ID", "KILO_SESSION_ID", "HERMES_SESSION_ID",
                    "GROK_SESSION_ID", "CODEX_THREAD_ID", "ANTIGRAVITY_CONFIG_REL_DIR"):
            env.pop(key, None)

        # T3 and custom commands can themselves launch one of the provider CLIs.
        nested = harness in {"t3code", "command"}
        if nested or harness == "opencode":
            if (config / "opencode").is_dir():
                env.setdefault("OPENCODE_CONFIG_DIR", str(config / "opencode"))
            link_files(config / "opencode", root / "config/opencode",
                       ("opencode.json", "opencode.jsonc", "cli.json"))
        if nested:
            link_files(Path(source.get("CLAUDE_CONFIG_DIR") or home / ".claude"), root / "claude",
                       ("settings.json", ".credentials.json"))
        if nested or harness == "codex":
            link_files(Path(source.get("CODEX_HOME") or home / ".codex"), root / "codex",
                       ("config.toml", "auth.json"))
        if nested or harness == "pi":
            link_files(Path(source.get("PI_CODING_AGENT_DIR") or home / ".pi/agent"), root / "pi",
                       ("settings.json", "models.json", "auth.json"))
        if nested or harness == "cline":
            cline = Path(source.get("CLINE_DIR") or home / ".cline")
            link_files(Path(source.get("CLINE_DATA_DIR") or cline / "data"), root / "cline/data",
                       ("settings/providers.json", "settings/global-settings.json"))
        if nested or harness == "kilo":
            link_files(config / "kilo", root / "config/kilo",
                       ("kilo.json", "kilo.jsonc", "kilocode.json", "kilocode.jsonc"))
            link_files(data / "kilo", root / "data/kilo", ("auth.json",))
        if nested or harness == "hermes":
            link_files(Path(source.get("HERMES_HOME") or home / ".hermes"), root / "hermes",
                       ("config.yaml", ".env", "auth.json"))
        if nested or harness == "antigravity":
            link_files(config / "antigravity", root / "config/antigravity", ("credential-user-scope",))
            link_files(home / ".gemini/antigravity-cli", private_home / ".gemini/antigravity-cli",
                       ("settings.json",))
        if nested or harness == "grokbuild":
            grok = Path(source.get("GROK_HOME") or home / ".grok")
            link_files(grok, root / "grok", ("config.toml", "auth.json"))
            env["GROK_AUTH_PATH"] = str(source.get("GROK_AUTH_PATH") or grok / "auth.json")
        yield env, root
