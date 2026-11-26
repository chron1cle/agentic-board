"""Independent stage trials for difficulty calibration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .feedback import VERDICT_ERROR, VERDICT_INCOMPLETE, VERDICT_INTEGRITY
from .orchestrator import Orchestrator, RunConfig
from .runrecord import SCHEMA_VERSION


def difficulty_groups(levels, expected_trials):
    """Order levels on matched trials. Keep ties in board order."""
    groups = {}
    for level in levels:
        if level["validTrials"] != expected_trials:
            continue
        key = (level["clears"], level["firstTryPasses"])
        groups.setdefault(key, []).append(level["stage"])
    return [{"clears": clears, "firstTryPasses": first_try, "stages": groups[(clears, first_try)]}
            for clears, first_try in sorted(groups, reverse=True)]


def calibrate(board, world, harness, adapter, model, seeds, out_dir, report=print):
    """Play each selected stage independently on each seed and record pass rates."""
    if not seeds:
        raise ValueError("calibration requires at least one seed")
    stages = RunConfig(board=board, world=world).stages()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=f"calibration-world-{world}-", dir=out_dir))
    levels = []
    invalid = {VERDICT_INTEGRITY, VERDICT_ERROR}

    for stage in stages:
        trials = []
        for trial, seed in enumerate(seeds, start=1):
            config = RunConfig(
                board=board, harness=harness, model=model, seed=seed, only=stage.id,
                out_dir=root / "trials", run_id=f"{stage.id}-{trial:03}",
            )
            orchestrator = Orchestrator(config, adapter)
            record = orchestrator.run()
            result = record.stages[0]
            started = [attempt for attempt in result.attempts if attempt.started]
            entry = {
                "seed": seed,
                "status": record.status,
                "cleared": result.cleared,
                "firstTry": result.cleared and result.attempts_used == 1,
                "attempts": len(started),
                "lastVerdict": result.attempts[-1].verdict if result.attempts else None,
                "record": f"trials/{record.run}/run.json",
            }
            entry["timedOut"] = any(attempt.timed_out for attempt in result.attempts)
            if started and started[-1].timed_out and (result.cleared or record.status == VERDICT_INCOMPLETE):
                attempt = started[-1]
                entry["timeoutArtifact"] = {
                    "attempt": attempt.n, "status": "pass" if result.cleared else "fail",
                    "checks": len(attempt.checks), "passedChecks": sum(check.ok for check in attempt.checks),
                }
            trials.append(entry)
            outcome = record.status
            if record.status not in invalid and record.status != VERDICT_INCOMPLETE:
                outcome = "cleared" if result.cleared else "failed"
            if result.cleared and entry["timedOut"]:
                outcome = "cleared at deadline"
            report(f"  {stage.id} · seed {seed} · {outcome}")

        usable = [trial for trial in trials if trial["status"] not in invalid
                  and trial["status"] != VERDICT_INCOMPLETE]
        levels.append({
            "stage": stage.id,
            "name": stage.name,
            "validTrials": len(usable),
            "firstTryPasses": sum(trial["firstTry"] for trial in usable),
            "clears": sum(trial["cleared"] for trial in usable),
            "budgetExhaustions": sum(trial["timedOut"] for trial in trials),
            "incompleteTrials": sum(trial["status"] == VERDICT_INCOMPLETE for trial in trials),
            "trials": trials,
        })

    groups = difficulty_groups(levels, len(seeds))
    planned = len(levels) * len(seeds)
    valid = sum(level["validTrials"] for level in levels)
    clears = sum(level["clears"] for level in levels)
    incomplete = sum(level["incompleteTrials"] for level in levels)
    invalid_count = planned - valid - incomplete
    summary = {
        "clears": clears, "validTrials": valid, "plannedTrials": planned,
        "incompleteTrials": incomplete, "invalidTrials": invalid_count,
        "clearRate": clears / valid if valid and not invalid_count else None,
    }
    report(f"  Independent clears: {clears}/{valid} decided trials · {incomplete} incomplete"
           f" · {invalid_count} invalid · {planned} planned")
    for group in groups:
        report(f"  {group['clears']}/{len(seeds)} clears, {group['firstTryPasses']} first try"
               f" · {', '.join(group['stages'])}")
    path = root / "calibration.json"
    path.write_text(json.dumps({
        "schema": SCHEMA_VERSION, "board": board.id, "boardVersion": board.version, "world": world,
        "harness": harness, "model": record.model, "seeds": seeds, "levels": levels,
        "summary": summary, "difficultyGroups": groups,
    }, indent=2) + "\n", encoding="utf-8")
    return path, levels
