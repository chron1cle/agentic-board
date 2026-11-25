# Agentic Board

A benchmark for coding agents, presented as a board game. Each board node is a coding
task with a machine-checkable outcome. An agent plays the board; how far it gets is
the result.

**Status: design phase.** The design is agreed and recorded in [DESIGN.md](DESIGN.md).
Nothing is built yet.

## The idea in one paragraph

An agent is dropped at stage 1 — something like *"edit this markdown file and make
exactly these changes"* — and given a fresh sandbox and a fresh harness session. When
it finishes, an oracle it cannot see or call checks the output. Pass, and it advances.
Fail, and it gets a terse error report and another attempt, from a pristine workspace
every time. Three failures on one stage ends the run, and the highest stage cleared
becomes its level. Stages escalate from single-file text edits to multi-hour
autonomous engineering, and every one of them has an outcome a machine can verify.

## Headline metrics

| Metric | Definition |
| --- | --- |
| Stage Reached | highest stage cleared |
| First-Try Rate | share of cleared stages cleared on attempt 1 |
| Feedback Uptake | P(pass on attempt k+1 \| failed attempt k) |

## Layout

```
DESIGN.md              the design record — start here
AGENTS.md              rules for agents working in this repo
SECURITY.md            secret-handling policy
docs/                  design detail
tools/audit-secrets.py secret audit gate
tools/install-hooks.sh installs the pre-commit hook
stages/                stage definitions (planned)
engine/                orchestrator, oracle, adapters (planned)
board/                 3D renderer (planned)
```

## Getting started

```bash
tools/install-hooks.sh                      # once per clone
python3 tools/audit-secrets.py --history    # audit the repo
```

## Contributing

Read [DESIGN.md](DESIGN.md) first. Decisions marked **DECIDED** were argued and
settled; reopening one needs a reason, not a preference.
