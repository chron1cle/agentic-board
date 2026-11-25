# Agentic Board — Design

A benchmark for coding agents, presented as a 3D board game. Each board node is a
coding task with a machine-checkable outcome. An agent plays the board; how far it
gets is the result.

Status: design agreed, nothing built yet. This file is the record of what we decided
and why. It is not aspirational — decisions marked **DECIDED** are settled.

---

## 1. What this is and is not

**DECIDED — Primary purpose: a rigorous benchmark.** Credibility is the product.
Verification, controls, and calibration get the investment. The 3D board is a
visualization of `run.json`, not a co-equal deliverable.

The system must answer one question defensibly: *given the same board and the same
seed, which harness+model gets further?* Everything else is in service of that.

---

## 2. Core loop

```
run = (harness+model, board_version, seed)

for stage in board:
    ledger = []
    for attempt in 1..3:
        sandbox = provision(stage, seed)              # byte-identical each attempt
        result  = harness.run(brief, ledger, budget)  # fresh process, fresh session
        verdict = oracle.run(sandbox.artifacts)       # privileged container
        if verdict.pass:
            award(stage, attempt); break
        ledger.append(verdict)
    else:
        game_over(stage)                              # highest cleared stage = level
```

### Attempt semantics

**DECIDED — attempts are stateless.** Each attempt gets a pristine workspace and a
cold harness session. Prior failures are passed to the agent only as the feedback
ledger (§4).

This was an explicit reversal. We first considered a persistent workspace with full
feedback, and rejected it: it makes attempt 2 a continuation of attempt 1, which
means attempts are not independent trials, which destroys the statistics that make a
leaderboard defensible. Stateless attempts also collapse the harness adapter to a
single `run()` call with no session-resume requirement, which widens the set of
harnesses we can support to essentially every headless one-shot CLI.

Consequences we accepted:

- The agent's own work is discarded between attempts. It sees *where* it failed, not
  what it tried.
- Cold-start cost triples for a struggling agent. Enforce a per-run token ceiling and
  record spend.
- The feedback ledger is the only channel between attempts, so it has to carry the
  entire signal (§4).

### Attempt boundary

An attempt ends when the harness process exits. The agent does not call the oracle
and never can. The oracle is owned by the orchestrator and runs in a separate
privileged container that mounts only declared artifacts.

### Verdicts

Three distinct failure verdicts, not one:

| Verdict | Meaning | Effect |
| --- | --- | --- |
| `failed` | oracle rejected the output | attempt consumed |
| `budget_exhausted` | ran out of tool calls or time, never finished | attempt consumed |
| `integrity_violation` | touched a protected path | run disqualified from the leaderboard |

---

## 3. Verification

"Exact match" applied naively fails correct solutions over trailing whitespace. Use
the weakest tier that is actually sound for the stage.

| Tier | Check | Use for |
| --- | --- | --- |
| A | exact bytes / sha256 | tiny deterministic text artifacts only |
| B | normalized match | text with irrelevant variance |
| C | diff-shape | "make exactly these changes" — asserts only intended lines changed |
| D | behavioral (hidden tests) | anything with behavior |
| E | differential / property-based | algorithms, parsers — compare to reference on seeded inputs |
| F | mutation score | "write your own tests" stages — inject bugs into their code |
| G | LLM judge | tie-breaks only, never gates progression |

Normalization vocabulary for tier B: strip trailing whitespace, collapse blank lines,
sort JSON keys, float tolerance, pinned locale and timezone.

### Determinism requirements

Without these, "exact output" is a coin flip. Pin in every stage image:

`PYTHONHASHSEED=0`, `LC_ALL=C`, `TZ=UTC`, `faketime` where output can depend on the
clock, sorted directory traversal.

### Anti-reward-hacking

This is where agentic benchmarks actually die. Non-negotiable:

- Tests and checkers mounted read-only, outside the writable workspace, checksummed
  and restored before every verification.
- Hidden tests use **different inputs** than visible ones. Kills hardcoded expected
  output.
- Sandbox scrubbed of git history, solution files, and the answer key.
- No network by default (§7).
- Protected-path hashes verified at every attempt boundary.
- **Controls.** Every stage ships with a no-op control (fix pre-applied) to measure
  false-pass rate, and a random baseline for the floor. A stage that passes for a
  do-nothing agent is broken and gets retired.

---

## 4. Feedback ledger

The only channel between attempts. Accumulated, never truncated, appended per failed
attempt:

```
## Attempt 1 — FAILED
- file-normalized: notes/meeting.md — 3 lines differ (14, 27, 31)
- diff-budget: 9 lines changed, limit 6
reveal: minimal — expected content withheld
tools used: 7   time: 42s
```

### Feedback budget

Full feedback is dangerous for exact-match stages: if the oracle prints a diff of the
target file, the diff *is* the answer and attempt 2 is free. So reveal is budgeted
per oracle tier, set per oracle block in the stage file as `reveal: minimal | standard | full`.

| Oracle tier | Reveal on failure | Withhold |
| --- | --- | --- |
| A/B exact + normalized | which check failed, count and line numbers of differences | expected content, the diff |
| C diff-shape | which constraint was violated | the intended diff |
| D hidden tests | test names, pass/fail per test | assertion bodies, expected values |
| E differential | failing input, got vs expected | nothing |
| F mutation | which mutant survived, its location | the patch |
| shell / exit code | full stderr | nothing |

Default `minimal` for tiers A–C, `full` for tier E.

### Sanitize the channel

Oracle output includes stderr from code the agent wrote. An agent can therefore get
arbitrary text into attempt 2's prompt through its own program's output. Treat all
oracle output as untrusted: strip control sequences, hard-truncate, wrap in delimiters
the agent is told is data. This is a real prompt-injection vector.

### Prompt envelope

Byte-identical structure for every harness, so outcome differences are attributable
to the agent and not to prompt drift.

```
<task>
{brief}
</task>

<prior_attempts failed="1" remaining="2">
{feedback_ledger}
</prior_attempts>

<rules>
Workspace is fresh; nothing from prior attempts survives.
Budget: {tool_budget} tool calls, {timeout_s} seconds.
</rules>
```

---

## 5. Scoring and metrics

```
stage_value(tier)   = 100 * (1 + 0.5 * (tier - 1))
attempt 1 pass      1.00x  + 20% first-try bonus
attempt 2 pass      0.75x
attempt 3 pass      0.50x
over budget         -5% per 25% over the stage tool/time budget
speed bonus         +5% under the reference-agent median wall time
failed stage        0, run ends
```

Global caps: per-stage wall clock across all attempts, whole-run wall clock, whole-run
token ceiling. All recorded. Without these the leaderboard measures whoever was
allowed to run longest.

### Headline metrics

| Metric | Definition |
| --- | --- |
| **Stage Reached** | highest stage cleared. The level. Per the game rules. |
| **First-Try Rate** | share of cleared stages cleared on attempt 1 |
| **Feedback Uptake** | P(pass on attempt k+1 \| failed attempt k) |

Feedback Uptake is the most interesting number in the system: it isolates whether an
agent can *use an error signal*, separate from whether it can solve a problem cold.
Two agents with identical Stage Reached can differ sharply here.

Because attempts are independent trials we can also report honest `pass@1`, `pass@3`
and confidence intervals per stage.

### Optional game mechanics

Not in v1, recorded so they are not lost:

- **Branch nodes** — opt-in harder variant for 2x points; failing a branch costs a
  life instead of ending the run.
- **Wager** — skip a node for a point cost.

---

## 6. Stage ladder

Difficulty escalates on two axes at once: problem complexity, and tool sophistication
(read → edit → search → shell → run tests → iterate → orchestrate).

Six tiers, six nodes on the spine each.

### Tier 1 — Precision · Plains of Edit
Tools: read, write, edit.

1. Edit `meeting.md` to make exactly these changes ← **the opening stage**
2. Fill a TODO stub so a given doctest passes
3. Reorder/dedupe a config file to match a spec
4. Repair broken JSON without changing its meaning
5. Split one module into two; imports still work
6. Rename a symbol across 3 files, zero behavior change

### Tier 2 — Reasoning over code · Caverns of Search
Adds: grep, glob, multi-file.

7. Fix an off-by-one so a hidden test passes
8. Find the one right function among decoys, change one line
9. Add the guard that stops a crash, given only a traceback
10. Extract duplicated logic into a helper (AST check + tests)
11. Write a migration touching 40 JSON files
12. Make a 3-failure test suite green

### Tier 3 — Produce an artifact · The Foundry
Adds: shell, execution.

13. Parse logs → CSV with exact rows
14. Aggregate data; stdout matches byte-for-byte
15. CSV → SQLite → answer a query
16. Generate an SVG/PNG with required properties
17. Produce a file whose sha256 matches — teaches determinism
18. Build a CLI whose `--help` and subcommand behavior match a spec

### Tier 4 — Diagnose · Labyrinth of Debug
Adds: reading failure evidence.

19. Fix a crash from a core dump / stack trace only
20. Turn a flaky race-condition test deterministic
21. 5x speedup under a measured time budget
22. Fix a dependency conflict in a broken environment
23. Recover data from a corrupt file
24. Fix a bug that only reproduces in a specific locale/timezone

### Tier 5 — Multi-step engineering · Spire of Systems

25. Implement a feature **and** tests that survive mutation testing
26. Build a tool, then use it to solve 3 instances
27. Integrate against a mock API: auth, pagination, rate limits, retries
28. Refactor a monolith into modules preserving a public API
29. Add concurrency without breaking a correctness oracle
30. Write a parser for a small DSL against hidden grammar tests

### Tier 6 — Autonomy · The Summit

31. Repo-wide codemod across 200 files
32. Reproduce a bug from a report, fix it, add a regression test
33. Profile, optimize, and *prove* the win
34. Recover a botched deploy with no git history
35. Add a plugin to a codebase never seen before
36. Final boss: diagnose across logs + code + config in a multi-service system

### Difficulty is measured, not asserted

Pilot every stage against three reference agents (strong / medium / weak) and *define*
difficulty by empirical pass rate. Sort the spine by measured pass rate, not
intuition. Expect to reshuffle heavily.

---

## 7. Sandboxing and network

**DECIDED — no network by default, per-stage opt-in allowlist.**

Blocks agents from fetching upstream fixes or the answer key. Tier 5 stages that need
network declare an allowlisted mock gateway in the stage file.

One OCI image per stage, digest pinned and recorded in the run. `setup.sh` builds the
workspace. Verification runs in a separate privileged container.

Stage file declares `protected:` paths; their hashes are verified at every attempt
boundary.

---

## 8. Stage schema

```yaml
id: s001-md-exact-edit
name: "The Ledger of Whispers"      # board flavor text
tier: 1
region: plains-of-edit
capabilities: [file-read, precise-edit]
brief: |
  Edit notes/meeting.md so that ...
sandbox:
  image: board/base@sha256:...
  setup: setup.sh
  network: none
  timeout_s: 300
  tool_budget: 12
  protected: [tests/, key/]
attempts: 3
oracle:
  - kind: file-normalized
    path: notes/meeting.md
    normalize: [strip-trailing-ws, collapse-blank]
    expect: key/meeting.md
    reveal: minimal
  - kind: diff-budget
    max-changed-lines: 6
    reveal: minimal
score: { base: 100, attempt_mult: [1.0, 0.75, 0.5] }
seedable: true
controls:
  noop: controls/fixed/            # fix pre-applied; must pass
  floor: controls/empty/           # do-nothing; must fail
```

## 9. Run record

Single source of truth for both scoring and the 3D replay.

```json
{
  "run": "r_01",
  "harness": "opencode",
  "model": "...",
  "board": "v3",
  "seed": 4821,
  "stages": [
    {
      "id": "s001",
      "attempts": [
        { "n": 1, "verdict": "fail", "evidence": "line 14 differs",
          "tools": 7, "s": 42, "tokens": 18300 },
        { "n": 2, "verdict": "pass", "tools": 4, "s": 19 }
      ],
      "points": 75
    }
  ],
  "final": { "stageReached": 14, "points": 812 }
}
```

---

## 10. Harness adapters

Do not couple to any one harness.

```
adapter.run({ brief, workspace, ledger, budget }) -> { verdict, events, usage }
events: message | tool.call{name,args} | file.write{path} | shell.exec{cmd,code} | done
```

No session resume is required, because attempts are stateless. Write adapters for the
headless one-shot modes: `opencode run`, `claude -p`, `codex exec`, `aider --message`,
and ACP where supported.

Capture raw transcripts next to normalized events. You will need them when someone
disputes a verdict.

---

## 11. The 3D board

The world encodes state; it is not decoration.

**Topology** — a linear ascending spine matching the rules, with opt-in branch nodes.
Six regions, one per tier, each matched to the capability it tests, so the art
direction *is* the difficulty legend.

| Region | Look | Capability |
| --- | --- | --- |
| Plains of Edit | tidy scriptorium, parchment, clean light | precision text |
| Caverns of Search | dark tunnels, lantern, scattered archives | code navigation |
| The Foundry | forges, conveyor output, sparks | producing artifacts |
| Labyrinth of Debug | broken machinery, steam, cracked floors | diagnosis |
| Spire of Systems | interlocking gears, bridges | multi-step engineering |
| The Summit | storm, single beacon | autonomy |

**Live feedback** — the piece travels node to node with eased camera follow. During an
attempt the node glows and emits one spark per tool call, so you can see an agent
flailing versus moving with intent. Failed attempts crack the node. Three crystals
beside the piece are the three attempts. A scrubber replays any archived run from
`run.json`.

**DECIDED — three.js / react-three-fiber.** Runs in a browser, trivially shareable,
easy to stream live state over WebSocket. Build it as a **replay engine first, live
second** — both read the same `run.json`.

A thin game-master service streams events over WebSocket/SSE and the renderer is a
dumb consumer:

`run.started · stage.entered · attempt.started · tool.call · attempt.ended ·
stage.cleared · piece.moved · run.ended`

---

## 12. Contamination

These tasks are largely in training data. Mitigate with **procedural seeding**: every
stage template generates fresh filenames, identifiers, and data values from the run
seed, and the oracle is generated from the same seed. Keep a bank of isomorphic
variants per template. Re-seed per run so a leaderboard run is never the memorized
instance.

---

## 13. Build order

1. **Oracle harness + stage schema** — CLI only, no graphics. 10 stages, 2 harnesses.
2. **Calibration** — reference agents, pass-rate curves, retire the broken stages.
3. **Event stream + `run.json`** — the contract everything else depends on.
4. **3D replay engine** reading recorded runs.
5. **Live mode** over WebSocket.
6. **Content bank to 36 stages** + procedural seeding + anti-cheat audit.

Ship 1–3 before touching WebGL. The verifier's credibility is the whole product.

---

## 14. Open questions

- Board and project name. `agentic-board` is a working placeholder.
- Which harnesses get adapters first, and which three models serve as calibration
  references.
- Whether a run is one agent on one board, or the same board seeded identically across
  N agents as a "table" — the latter makes comparison tighter.
- Public data policy: are transcripts and `run.json` for every leaderboard run
  published, or only aggregate scores?
- Versioning: how a board version is frozen, and whether old versions stay playable.
- Sandbox threat model: the engine runs untrusted agent-generated code. That needs its
  own document before the engine is built. See [SECURITY.md](SECURITY.md).

## 15. Repo hygiene

Secrets never enter this repo. `tools/audit-secrets.py` is the in-repo gate, run by a
pre-commit hook (`tools/install-hooks.sh`) and by CI on every push including full
history. See [SECURITY.md](SECURITY.md).
