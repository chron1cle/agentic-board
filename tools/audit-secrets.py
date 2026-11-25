#!/usr/bin/env python3
"""Secret audit for this repository. Stdlib only, no install step.

Scans the working tree and, with --history, every blob in git history.
Exit code 1 when findings are not allowlisted.

  python3 tools/audit-secrets.py              # working tree
  python3 tools/audit-secrets.py --history    # working tree + all git blobs
  python3 tools/audit-secrets.py --json       # machine readable
  python3 tools/audit-secrets.py --baseline    # write allowlist entries to stdout

Findings are fingerprinted as path:rule:fingerprint. Add a fingerprint to
.secrets-allow to accept a known false positive. Allowlist the fingerprint,
never the path, so a real secret on an allowlisted file is still caught.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_FILE = REPO_ROOT / ".secrets-allow"
SELF = Path(__file__).resolve()

MAX_FILE_BYTES = 2 * 1024 * 1024
MIN_ENTROPY_TOKEN = 20
ENTROPY_THRESHOLD = 4.0

# Directories never worth scanning.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".next", ".turbo", "target", ".gradle", "vendor", ".tox", ".cache",
}

# Extensions that are binary or notorious for high-entropy noise.
SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".bz2", ".xz", ".tar", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp4",
    ".mp3", ".wav", ".ogg", ".so", ".dll", ".dylib", ".bin", ".exe", ".class",
    ".pyc", ".lock", ".snap",
}

# Basenames notorious for high-entropy noise that is not a credential.
SKIP_BASENAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock"}

# This tool contains credential patterns by design.
SELF_EXCLUDED = {SELF}

# Lines matching these are treated as documentation, not credentials.
CONTEXT_SUPPRESS = re.compile(
    r"(?i)\b(sha256|sha512|sha1|md5|commit|checksum|digest|hash of|example|"
    r"placeholder|your[-_ ]?(key|token|secret)|xxx|redacted|<[^>]+>)"
)

# Value must look like a credential for generic assignment rules to fire.
LOOKS_SECRET = re.compile(r"[A-Za-z0-9+/_\-\.=]{16,}")


@dataclass
class Rule:
    rid: str
    description: str
    pattern: re.Pattern
    severity: str = "HIGH"

    def __post_init__(self) -> None:
        self.pattern = re.compile(self.pattern)


RULES: list[Rule] = [
    Rule("github-token", "GitHub personal access token",
         r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    Rule("github-fine-grained", "GitHub fine-grained token",
         r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    Rule("aws-access-key", "AWS access key id",
         r"\b(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b"),
    Rule("aws-secret-key", "AWS secret access key assignment",
         r"(?i)aws.{0,25}(secret|sk).{0,25}['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
    Rule("openai-key", "OpenAI API key",
         r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    Rule("anthropic-key", "Anthropic API key",
         r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
    Rule("stripe-key", "Stripe secret key",
         r"\b[rpk]_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    Rule("slack-token", "Slack token",
         r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    Rule("slack-webhook", "Slack incoming webhook",
         r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+"),
    Rule("google-api-key", "Google API key",
         r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    Rule("oauth-client-secret", "Google/OAuth client secret",
         r"\b[0-9]+-[0-9a-z]{20,}\.apps\.googleusercontent\.com\b"),
    Rule("sendgrid-key", "SendGrid API key",
         r"\bSG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\b"),
    Rule("twilio-key", "Twilio credential",
         r"\b(?:AC[a-f0-9]{32}|SK[a-f0-9]{32})\b"),
    Rule("npm-token", "npm access token",
         r"\bnpm_[A-Za-z0-9]{30,}\b"),
    Rule("pypi-token", "PyPI upload token",
         r"pypi-AgEIcHlwaS5vcmc[A-Za-z0-9_\-]{20,}"),
    Rule("discord-webhook", "Discord webhook",
         r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_\-]{20,}"),
    Rule("telegram-bot-token", "Telegram bot token",
         r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,}\b"),
    Rule("private-key-block", "PEM private key block",
         r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY( BLOCK)?-----"),
    Rule("jwt", "JSON Web Token",
         r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
    Rule("basic-auth-url", "Credentials embedded in URL",
         r"[a-z][a-z0-9+.\-]*://[^/\s:@]{1,64}:[^/\s:@]{1,64}@"),
    Rule("huggingface-token", "Hugging Face token",
         r"\bhf_[A-Za-z0-9]{30,}\b"),
    Rule("gitlab-token", "GitLab token",
         r"\bglpat-[A-Za-z0-9_\-]{20,}\b"),
    Rule("generic-assignment", "Generic secret-looking assignment",
         r"(?i)\b(?:secret|token|api[_-]?key|apikey|access[_-]?key|private[_-]?key|"
         r"client[_-]?secret|auth[_-]?(?:token|key)|password|passwd|pwd)"
         r"\b\s*[:=]\s*['\"]?([^'\"\s]{16,})['\"]?"),
    Rule("env-file", "File that conventionally holds secrets",
         r"(?s).", severity="MEDIUM"),
]

# Rules that match on filename rather than content.
FILENAME_RULES: list[tuple[str, re.Pattern, str]] = [
    ("env-file", re.compile(r"(^|/)\.env(\..+)?$|\.env$"), "HIGH"),
    ("pem-file", re.compile(r"\.(pem|key|p12|pfx|jwk)$"), "HIGH"),
    ("ssh-key-file", re.compile(r"(^|/)(id_rsa|id_ed25519|id_ecdsa)$"), "HIGH"),
    ("credential-file",
     re.compile(r"(^|/)(credentials|credentials\.json|token\.json|\.netrc|"
                r"\.npmrc|\.pypirc|service-account.*\.json)$"), "HIGH"),
    ("terraform-vars", re.compile(r"\.tfvars(.*\.json)?$"), "MEDIUM"),
]

ENTROPY_OK = re.compile(r"[A-Za-z0-9+/=_\-]{%d,}" % MIN_ENTROPY_TOKEN)


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    description: str
    severity: str
    match: str
    source: str = "worktree"
    fingerprint: str = ""

    def __post_init__(self) -> None:
        digest = hashlib.sha256(self.match.encode("utf-8", "replace")).hexdigest()
        self.fingerprint = f"{self.path}:{self.rule}:{digest[:12]}"

    def redacted(self) -> str:
        text = self.match.replace("\n", "\\n")
        if len(text) <= 12:
            return text[:2] + "*" * max(0, len(text) - 2)
        return f"{text[:6]}…{text[-4:]} ({len(self.match)} chars)"

    def as_dict(self) -> dict:
        return {
            "path": self.path, "line": self.line, "rule": self.rule,
            "description": self.description, "severity": self.severity,
            "source": self.source, "fingerprint": self.fingerprint,
            "match": self.redacted(),
        }


def shannon(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def load_allowlist() -> set[str]:
    if not ALLOWLIST_FILE.exists():
        return set()
    entries = set()
    for raw in ALLOWLIST_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.add(line)
    return entries


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


_TRACKED: set[str] | None = None


def tracked_files() -> set[str]:
    """Paths git actually tracks. A force-added .env is tracked even though
    .gitignore matches it, and must still be scanned."""
    global _TRACKED
    if _TRACKED is None:
        try:
            out = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
            )
            _TRACKED = {p for p in out.stdout.split("\0") if p}
        except (OSError, subprocess.SubprocessError):
            _TRACKED = set()
    return _TRACKED


def is_publishable(path: Path) -> bool:
    """True when git would take this file into the published repo."""
    name = rel(path)
    if name in tracked_files():
        return True
    try:
        out = subprocess.run(
            ["git", "check-ignore", "-q", name],
            cwd=REPO_ROOT, capture_output=True, timeout=20,
        )
        return out.returncode != 0
    except (OSError, subprocess.SubprocessError):
        return True


def iter_worktree_files():
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path in SELF_EXCLUDED or path.suffix.lower() in SKIP_EXT:
                continue
            if name in SKIP_BASENAMES:
                continue
            if not is_publishable(path):
                continue
            yield path


def scan_content(path: Path, text: str, source: str) -> list[Finding]:
    findings: list[Finding] = []
    display = rel(path) if source == "worktree" else f"{rel(path)}@{source}"

    for rid, pattern, severity in FILENAME_RULES:
        if pattern.search(str(path).replace(os.sep, "/")):
            findings.append(Finding(display, 0, rid,
                                    "filename suggests a secret-bearing file",
                                    severity, str(path).replace(os.sep, "/"), source))

    if path.suffix.lower() in SKIP_EXT:
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        if len(line) > 4000 or CONTEXT_SUPPRESS.search(line):
            continue
        for rule in RULES:
            if rule.rid == "env-file":
                continue
            if rule.rid == "generic-assignment":
                for m in rule.pattern.finditer(line):
                    value = m.group(1) if m.groups() else m.group(0)
                    if LOOKS_SECRET.fullmatch(value) and shannon(value) >= 3.0:
                        findings.append(Finding(display, lineno, rule.rid,
                                                rule.description, rule.severity,
                                                value, source))
                continue
            for m in rule.pattern.finditer(line):
                findings.append(Finding(display, lineno, rule.rid,
                                        rule.description, rule.severity,
                                        m.group(0), source))

        # High-entropy fallback for tokens with no recognizable prefix.
        for token in ENTROPY_OK.findall(line):
            if len(token) < MIN_ENTROPY_TOKEN or token.isdigit():
                continue
            if len(token) == 40 and re.fullmatch(r"[0-9a-f]{40}", token):
                continue  # git object id
            if shannon(token) < ENTROPY_THRESHOLD:
                continue
            findings.append(Finding(display, lineno, "high-entropy",
                                    "high-entropy string with no known prefix",
                                    "MEDIUM", token, source))
    return findings


def scan_worktree() -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_worktree_files():
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            data = path.read_bytes()
            if b"\x00" in data[:4096]:
                continue
            findings += scan_content(path, data.decode("utf-8", "replace"), "worktree")
        except OSError:
            continue
    return findings


def scan_history(max_blob_bytes: int = 4 * 1024 * 1024) -> list[Finding]:
    """Scan every blob reachable from any ref. Catches what was already pushed."""
    try:
        listing = subprocess.run(
            ["git", "rev-list", "--objects", "--all"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        )
        if listing.returncode != 0:
            return []
    except (OSError, subprocess.SubprocessError):
        return []

    wanted: dict[str, str] = {}
    for row in listing.stdout.splitlines():
        parts = row.split(" ", 1)
        if len(parts) == 2 and not parts[1].endswith("/"):
            wanted[parts[0]] = parts[1]

    findings: list[Finding] = []
    batch: list[str] = list(wanted)
    for i in range(0, len(batch), 500):
        chunk = batch[i:i + 500]
        try:
            proc = subprocess.run(
                ["git", "cat-file", "--batch"],
                cwd=REPO_ROOT, input="\n".join(chunk),
                capture_output=True, text=True, timeout=300,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        # cat-file --batch emits "<sha> <type> <size>\n<content>\n"
        lines = proc.stdout.split("\n")
        idx = 0
        while idx < len(lines):
            header = lines[idx].split(" ")
            if len(header) < 3 or header[1] != "blob":
                idx += 1
                continue
            sha, _, size_text = header[0], header[1], header[2]
            try:
                size = int(size_text)
            except ValueError:
                idx += 1
                continue
            body = "\n".join(lines[idx + 1: idx + 1 + size]) if size else ""
            idx += 2 + size
            name = wanted.get(sha, sha)
            if Path(name).suffix.lower() in SKIP_EXT or Path(name).name in SKIP_BASENAMES:
                continue
            if size > max_blob_bytes:
                continue
            pseudo = REPO_ROOT / name
            if pseudo in SELF_EXCLUDED:
                continue
            findings += scan_content(pseudo, body, sha[:10])
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit this repo for secrets.")
    parser.add_argument("--history", action="store_true",
                        help="also scan every blob in git history")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--baseline", action="store_true",
                        help="print allowlist entries for current findings")
    args = parser.parse_args()

    if not (REPO_ROOT / ".git").exists():
        print("not a git repository", file=sys.stderr)
        return 2

    findings = scan_worktree()
    if args.history:
        existing = {(f.path, f.line, f.rule) for f in findings}
        findings += [f for f in scan_history()
                     if (f.path, f.line, f.rule) not in existing]

    allow = load_allowlist()
    blocked = [f for f in findings if f.fingerprint not in allow]
    accepted = [f for f in findings if f.fingerprint in allow]

    if args.baseline:
        for f in sorted(findings, key=lambda x: x.fingerprint):
            print(f.fingerprint)
        return 0

    if args.json:
        print(json.dumps({
            "findings": [f.as_dict() for f in blocked],
            "allowlisted": len(accepted),
            "ok": not blocked,
        }, indent=2))
        return 1 if blocked else 0

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    blocked.sort(key=lambda f: (order.get(f.severity, 9), f.path, f.line))

    if not blocked:
        print(f"secret audit clean — {len(accepted)} allowlisted finding(s)")
        return 0

    print(f"secret audit found {len(blocked)} possible secret(s):\n")
    for f in blocked:
        loc = f"{f.path}:{f.line}" if f.line else f.path
        print(f"  [{f.severity}] {f.rule:22} {loc}")
        print(f"           {f.description}")
        print(f"           {f.redacted()}")
        print(f"           allowlist: {f.fingerprint}\n")
    print("Fix: remove the value from the file and from history, then rotate it.")
    print("If this is a false positive, add the fingerprint to .secrets-allow.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
