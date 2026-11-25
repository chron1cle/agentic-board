# Agentic Board

A benchmark for coding agents, presented as a board game. Each board node is a coding
task with a machine-checkable outcome. An agent plays the board; how far it gets is
the result.

Everything here runs on one machine, offline, with no servers and no external
services. The engine is Python with exactly one dependency, PyYAML; a test fails if a
second one appears. The tests are `unittest`. The only network traffic in a benchmark
is whatever the harness itself needs to reach its model.

## The idea in one paragraph

An agent is dropped at stage 1 — something like *"edit this markdown file and make
exactly these changes"* — and given a fresh sandbox and a fresh harness session. When
it finishes, an oracle it cannot see or call checks the output. Pass, and it advances.
Fail, and it gets a terse error report and another attempt, from a pristine workspace
every time. Three failures on one stage ends the run, and the highest stage cleared
becomes its level. Stages escalate from single-file text edits to a whole-codebase
migration, and every one of them has an outcome a machine can verify.

## Headline metrics

| Metric | Definition | Why it matters |
| --- | --- | --- |
| **Stage Reached** | highest stage cleared | the level. One number, comparable across harnesses |
| **First-Try Rate** | share of cleared stages cleared on attempt 1 | does it get it right, or does it brute-force |
| **Feedback Uptake** | P(pass on attempt k+1 \| it failed attempt k) | can it use an error message |

Supporting numbers (tool calls, tokens, wall clock, attempts) are recorded too, but
they are diagnostics, not the score.

## The board

Ten stages, one spine, six regions. `python3 -m engine validate` prints the same
table from the specs.

| # | Stage | Tier | Region | What it tests | Base |
| --- | --- | --- | --- | --- | --- |
| 1 | `s001-exact-edit` | 1 | Plains of Edit | make exactly three edits, change nothing else | 100 |
| 2 | `s002-json-repair` | 1 | Plains of Edit | repair malformed JSON against a schema | 100 |
| 3 | `s003-rename-symbol` | 2 | Caverns of Search | rename a symbol across a small codebase | 150 |
| 4 | `s004-offbyone` | 2 | Caverns of Search | find and fix an off-by-one in failing tests | 150 |
| 5 | `s005-log-search` | 2 | Caverns of Search | search a large log for the answers to questions | 150 |
| 6 | `s006-sessionizer` | 3 | The Foundry | write a module to a written spec, hidden tests | 200 |
| 7 | `s007-cli-spec` | 3 | The Foundry | build a CLI that matches a spec exactly, incl. exit codes | 200 |
| 8 | `s008-pipeline-fix` | 4 | Labyrinth of Debug | fix a broken concurrent pipeline under a hidden checker | 250 |
| 9 | `s009-tests-that-test` | 5 | Spire of Systems | write tests that kill injected mutants | 300 |
| 10 | `s010-codemod-migration` | 6 | The Summit | migrate a codebase from a legacy API to a v2 SDK | 350 |

Base is `100 × (1 + 0.5 × (tier − 1))`. Cleared on attempt 1 you get base × 1.2,
attempt 2 × 0.75, attempt 3 × 0.50, with a small penalty for blowing the tool
budget. A perfect run is 2340 points; the number that actually matters is stage
reached, because points reward a run that a rule ended fairly.

Every stage ships two **controls**: a `fixed` workspace that must pass the oracle and
an `empty` one that must fail it. A stage whose oracle accepts nothing is not a stage,
so the controls are checked in CI:

```bash
python3 -m engine controls
```

## Quickstart

Requirements: Python 3.12+ and one package, PyYAML. Node 20+ only if you want the 3D
viewer.

```bash
pip install -r requirements.txt            # pyyaml, and that is the whole list
tools/install-hooks.sh                     # once per clone: the secret audit hook
python3 -m engine validate                 # every stage + the board parse and agree
python3 -m engine controls                 # fixed control passes, do-nothing fails
python3 -m unittest discover -s tests -t . # the engine's own test suite
```

After that one install, nothing here needs credentials or a network: the tests are
stdlib `unittest`, the fixtures are in-repo, and no oracle reaches outside the
sandbox. If those four are green, the instrument is sound.

## Running a benchmark

### With the fake harness (no model, no cost)

The `fake` harness is a scripted agent used by the tests. It is the fastest way to
exercise the whole pipeline — sandbox provisioning, oracles, scoring, run records:

```bash
python3 -m engine run --harness fake --run-id smoke
```

### The reference run (proves the board is solvable)

`--harness solve` is not an agent. It plays each stage by installing that stage's own
`fixed` control, and it exists to answer a question you must be able to answer before
you blame a model: *is this board completable at all?*

```bash
python3 -m engine run --harness solve --run-id reference
# stage reached 10 / 10, points 2340.0, first-try rate 100%
```

If that ever stops reaching stage 10, a stage is broken. CI runs it for exactly that
reason. It is also the cheapest way to get a full board to look at in the viewer.

### With a real harness

`opencode` is wired up. Put your provider credentials wherever opencode normally
finds them, then:

```bash
# play the whole board with opencode's configured default model
python3 -m engine run --harness opencode --run-id opencode-default

# or name a model explicitly
python3 -m engine run --harness opencode --model provider/model --run-id run-2
```

Useful flags:

| Flag | Meaning |
| --- | --- |
| `--board boards/v1.yaml` | which board (default: the ten-stage spine) |
| `--limit N` | play only the first N stages — good for a cheap calibration run |
| `--only s006-sessionizer` | one stage, for authoring or debugging |
| `--seed N` | recorded in the run record; stages are deterministic so this is bookkeeping |
| `--out DIR` | where runs land (default `runs/`) |
| `--quiet` | just the summary, no live event stream |

A full board costs up to 3 attempts per stage and up to ~3.5 model-hours. Budget
accordingly, and use `--limit 3` when you are calibrating.

### What a run leaves behind

```
runs/<run-id>/run.json                 score sheet + replay tape
runs/<run-id>/events.jsonl             every engine event, in order
runs/<run-id>/<stage>/attempt<N>/      the workspace the agent actually had
runs/<run-id>/<stage>/attempt<N>.transcript.json   prompt + raw harness output
runs/index.json                        every run, for the results viewer
```

`run.json` is the only thing the viewer reads. That is deliberate: the score sheet,
the replay tape, and the board state are one file, so the renderer can never
disagree with the scoreboard.

### A published example

One real run is committed: `runs/opencode-default/`, played by opencode v2.4.1 with
its configured default model (`ms-s1/halogen`) on board v1, seed 1. Only `run.json`
and `events.jsonl` are in git — scores and verdicts, no paths and no transcripts.

```
opencode / default (ms-s1/halogen)   board agentic-board v1   seed 1
stage reached   10 / 10        first-try rate  100%
points          2340.0         feedback uptake 0%
tools           62             time            17m34s
tokens          194,347
```

| # | Stage | Tier | Tools | Wall time |
| --- | --- | --- | --- | --- |
| 1 | `s001-exact-edit` | 1 | 5 | 21s |
| 2 | `s002-json-repair` | 1 | 4 | 27s |
| 3 | `s003-rename-symbol` | 2 | 4 | 26s |
| 4 | `s004-offbyone` | 2 | 4 | 39s |
| 5 | `s005-log-search` | 2 | 4 | 25s |
| 6 | `s006-sessionizer` | 3 | 4 | 133s |
| 7 | `s007-cli-spec` | 3 | 6 | 219s |
| 8 | `s008-pipeline-fix` | 4 | 13 | 134s |
| 9 | `s009-tests-that-test` | 5 | 6 | 238s |
| 10 | `s010-codemod-migration` | 6 | 12 | 193s |

Read that honestly, in both directions. A clean sweep on the first attempt of every
stage says this model is **at or above the top of this board**: `s009` (write tests
that kill injected mutants) and `s010` (migrate a codebase to a v2 SDK, verified by a
hidden checker that includes deleted files) fell to four to twelve tool calls each.
So `v1` will not separate this model from a slightly better one — it separates weak
agents from competent ones, and its ceiling is now measured. The fix is more stages
above tier 6, not softer oracles.

Two numbers in that block are artifacts of a perfect run, not achievements. Feedback
uptake is 0% because there was no failed attempt to learn from; the metric is only
meaningful below 100% first-try. And the tool counts are low partly because a single
turn of a strong agent does what a weaker one takes ten calls to stumble into.

To see it: `python3 -m engine serve`, then open the Results tab and press Replay.

## The viewer

Two surfaces, one app: the **3D board** (a stage is a node on an ascending spine,
grouped into regions, with a piece that travels it) and the **results table** (every
run you have ever recorded, sortable, with a **Replay** button that animates the
score climbing stage by stage).

```bash
cd board
npm install
npm run build            # writes board/dist
cd ..
python3 -m engine serve  # http://localhost:8088/
```

`engine serve` rebuilds `runs/index.json` first, then serves exactly two prefixes:
the built viewer and the runs directory. It does not serve the repository, so stage
answer keys and `.git` stay off the network.

For development, `cd board && npm run dev` gives a hot-reloading server on :5173 that
proxies `/runs` to an `engine serve` on :8088.

In the app:

- **Board** — the 3D spine. Click a node, or a row in the sidebar, to focus it; the
  three crystals next to a focused node are its three attempts, lit by verdict.
- **Score replay** — the same run as a chart. Press **Replay** and the playhead walks
  the spine while the cumulative score fills in. Speed control and a scrub bar.
- **Results** — one row per run, sorted by stage reached. **Replay** on any row jumps
  straight into that run's score animation.

## Adding a stage

1. `stages/<id>/stage.yaml` — brief, tier, budget, and an oracle spec (one of
   `file_exact`, `file_normalized`, `json_equal`, `diff_budget`, `command`, `script`,
   `differential`, `mutation`, `timing`).
2. `stages/<id>/workspace/` — the fixture the agent gets.
3. `stages/<id>/oracle/` — the verification. Never copied into the sandbox, never
   callable by the agent.
4. `stages/<id>/controls/{fixed,empty}` — the two controls.
5. Add the id to `boards/v1.yaml`, then `python3 -m engine validate && python3 -m engine controls`.

Oracle scripts run with the working directory set to the sandbox workspace, so use
cwd-relative paths for agent files and `__file__`-relative paths for hidden fixtures.

## Honest limits

- **The local sandbox is not a security boundary.** Attempts run as your user, so an
  agent that wanted to escape could. What the sandbox gives you is determinism (a
  byte-identical workspace per attempt, checked by fingerprint) and accident
  proofing (protected paths, no network by default, integrity checks that disqualify
  a run that touches the oracle). Real isolation means the container path described in
  DESIGN.md, which is not implemented here.
- **Scores are comparable within a board version, not across versions.** Changing a
  stage changes what the number means.
- **A stage is only as good as its oracle.** That is why the controls are enforced.

## Layout

```
DESIGN.md              the design record — start here
AGENTS.md              rules for agents working in this repo
SECURITY.md            secret-handling policy
boards/v1.yaml         the ten-stage spine
stages/                stage definitions: workspace, oracle, controls
engine/                orchestrator, oracles, sandbox, harness adapters, CLI
engine/harness/        one adapter per harness (opencode, fake, solve)
board/                 react-three-fiber board + results viewer
tests/                 engine unit tests
tools/audit-secrets.py secret audit gate (pre-commit + CI)
docs/                  design detail
runs/opencode-default/ one published run, committed so the viewer has data
```

## Contributing

Read [DESIGN.md](DESIGN.md) first. Decisions marked **DECIDED** were argued and
settled; reopening one needs a reason, not a preference.

Before committing, `python3 tools/audit-secrets.py`. This repo is public and every
commit is permanent.
