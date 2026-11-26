"""The feedback ledger and the prompt envelope.

The ledger is the only channel between attempts, so it carries the entire
signal and nothing more. Reveal levels are enforced here: for exact-match
stages the diff is the answer, so showing it would make attempt 2 free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .oracles import Check, sanitize

MAX_LEDGER = 6000

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_INCOMPLETE = "incomplete"
VERDICT_BUDGET = "budget_exhausted"  # Recorded by runners before schema 3.
VERDICT_INTEGRITY = "integrity_violation"
VERDICT_ERROR = "infrastructure_error"


@dataclass
class AttemptRecord:
    n: int
    verdict: str
    checks: list[Check] = field(default_factory=list)
    tool_calls: int = 0
    seconds: float = 0.0
    tokens: int = 0
    note: str = ""
    started: bool = True
    tools_reported: bool = True
    tokens_reported: bool = True
    timed_out: bool = False

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "started": self.started,
            "timed_out": self.timed_out,
            "verdict": self.verdict,
            "tools": self.tool_calls,
            "tools_reported": self.tools_reported,
            "s": round(self.seconds, 2),
            "tokens": self.tokens,
            "tokens_reported": self.tokens_reported,
            "note": self.note,
            "checks": [c.as_dict() for c in self.checks],
        }


def render_check(check: Check) -> list[str]:
    """One check -> ledger lines, honoring its reveal level."""
    mark = "ok" if check.ok else "FAILED"
    lines = [f"- {check.name}: {mark}" + (f" — {check.detail}" if check.detail else "")]
    if check.evidence and check.reveal == "full":
        indented = "\n".join(f"    {line}" for line in check.evidence.splitlines()[:40])
        lines.append(f"    evidence:\n{indented}")
    elif check.evidence and check.reveal == "standard":
        lines.append(f"    ({len(check.evidence.splitlines())} line(s) of detail withheld)")
    else:
        if check.evidence:
            lines.append("    (expected content withheld)")
    return lines


def render_ledger(attempts: list[AttemptRecord]) -> str:
    """Accumulated failure history for the prompt. Never truncated per attempt."""
    if not attempts:
        return ""
    blocks: list[str] = []
    for attempt in attempts:
        if attempt.verdict == VERDICT_PASS:
            continue
        head = f"## Attempt {attempt.n} — {attempt.verdict.upper()}"
        lines = [head]
        for check in attempt.checks:
            lines += render_check(check)
        if attempt.note:
            lines.append(f"- note: {attempt.note}")
        lines.append(f"tools used: {attempt.tool_calls}   time: {attempt.seconds:.0f}s")
        blocks.append("\n".join(lines))
    text = "\n\n".join(blocks)
    # Defense in depth: check details originate from agent-controlled output.
    return sanitize(text, MAX_LEDGER)


def build_prompt(brief: str, attempts: list[AttemptRecord], attempts_left: int,
                 tool_budget: int, timeout_s: int) -> str:
    """Byte-stable envelope, identical for every harness (DESIGN.md §4)."""
    ledger = render_ledger(attempts)
    parts = ["<task>", brief.strip(), "</task>"]
    if ledger:
        parts += [
            f'<prior_attempts failed="{len(attempts)}" remaining="{attempts_left}">',
            "Your previous attempts did not pass. The workspace is fresh, so none",
            "of your earlier edits survive. Use the reports below to aim better.",
            "",
            ledger,
            "</prior_attempts>",
        ]
    parts += [
        "<rules>",
        "Work only inside the current working directory.",
        "The workspace is fresh; nothing from prior attempts survives.",
        f"Budget: about {tool_budget} tool calls and {timeout_s} seconds.",
        "When you are finished, stop. Do not wait for confirmation.",
        "</rules>",
    ]
    return "\n".join(parts)
