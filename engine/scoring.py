"""Scoring and headline metrics.

Formulas are fixed by DESIGN.md §5. Keep them here and nowhere else, so a
leaderboard number can always be traced back to one place.
"""

from __future__ import annotations

ATTEMPT_MULTIPLIER = {1: 1.00, 2: 0.75, 3: 0.50}
FIRST_TRY_BONUS = 0.20
OVER_BUDGET_PENALTY = 0.05      # per 25% over budget
SPEED_BONUS = 0.05


def stage_value(tier: int, base: int = 100) -> int:
    return int(base * (1 + 0.5 * (tier - 1)))


def budget_penalty(used: float, budget: float) -> float:
    """-5% per 25% over the stage budget. Under budget is never punished."""
    if budget <= 0 or used <= budget:
        return 0.0
    over_ratio = (used - budget) / budget
    return OVER_BUDGET_PENALTY * int(over_ratio / 0.25)


def score_stage(tier: int, attempt_n: int, tools_used: int = 0, tool_budget: int = 0,
                seconds: float = 0.0, reference_seconds: float | None = None,
                base: int = 100) -> float:
    """Points for one cleared stage. A failed stage scores zero."""
    value = stage_value(tier, base)
    mult = ATTEMPT_MULTIPLIER.get(attempt_n, 0.5)
    points = value * mult
    if attempt_n == 1:
        points += value * FIRST_TRY_BONUS
    points *= (1.0 - budget_penalty(tools_used, tool_budget))
    if reference_seconds and 0 < seconds < reference_seconds:
        points *= (1.0 + SPEED_BONUS)
    return round(points, 2)


def first_try_rate(stage_results) -> float:
    """Share of cleared stages that were cleared on attempt 1."""
    cleared = [r for r in stage_results if r.cleared]
    if not cleared:
        return 0.0
    return round(sum(1 for r in cleared if r.attempts_used == 1) / len(cleared), 4)


def feedback_uptake(stage_results) -> float:
    """P(pass on attempt k+1 | failed attempt k), pooled over the whole run.

    This is the most interesting number in the system: it separates an agent
    that can use an error report from one that just retries until lucky.
    """
    transitions = passes = 0
    for result in stage_results:
        for earlier, later in zip(result.attempts, result.attempts[1:]):
            if earlier.verdict == "fail":
                transitions += 1
                if later.verdict == "pass":
                    passes += 1
    if not transitions:
        return 0.0
    return round(passes / transitions, 4)
