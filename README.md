# Agentic Board

A benchmark for coding agents, presented as a board game. Each board node is a coding
task with a machine-checkable outcome. An agent plays the board; how far it gets is
the result.

The engine and reference controls run locally with Python and PyYAML. The CLI
harnesses can reach their model providers and inherit the operator's
network access and configuration.

## The idea in one paragraph

An agent is dropped at stage 1 — something like *"edit this markdown file and make
exactly these changes"* — and given a fresh sandbox and a fresh harness session. When
it finishes, the engine calls the stage oracle to check the output. Pass, and it advances.
Fail, and it gets a terse error report and another attempt, from a pristine workspace
every time. Three failures on one stage ends the run, and the highest stage cleared
becomes its level. World 1 progresses from single-file edits to multi-module
migration and test design. World 2 adds a routing rule at each level. World 3
uses independent engineering challenges with seeded checks.

## Headline metrics

| Metric | Definition | Why it matters |
| --- | --- | --- |
| **Stage Reached** | highest stage cleared | the level. One number, comparable across harnesses |
| **First-Try Rate** | share of cleared stages cleared on attempt 1 | does it get it right, or does it brute-force |
| **Feedback Uptake** | fraction of observed retries that pass after an oracle rejection | retry conversion under the actual feedback and time budgets |

Runs record observed tool calls, harness time, reported tokens, and started
attempts. Tool counts affect points and depend on how the harness exposes its
tools. Feedback uptake is shown with its retry count or left blank when there
were no eligible retries.

## The board

Board v4 has three worlds of ten levels. Level 1 opens each world and level 10
is its intended hardest test. A stage ID identifies a task across releases.
Its world and level number come from the selected board version. `python3 -m engine validate` lists all stages.

| # | Stage | Tier | Region | What it tests | Base |
| --- | --- | --- | --- | --- | --- |
| 1-1 | `s001-exact-edit` | 1 | Plains of Edit | make exactly three edits, change nothing else | 100 |
| 1-2 | `s002-json-repair` | 1 | Plains of Edit | repair malformed JSON against a schema | 100 |
| 1-3 | `s005-log-search` | 2 | Caverns of Search | search a large log for the answers to questions | 150 |
| 1-4 | `s003-rename-symbol` | 2 | Caverns of Search | rename a symbol across a small codebase | 150 |
| 1-5 | `s004-offbyone` | 2 | Caverns of Search | find and fix an off-by-one in failing tests | 150 |
| 1-6 | `s006-sessionizer` | 3 | The Foundry | write a module to a written spec, hidden tests | 200 |
| 1-7 | `s008-pipeline-fix` | 4 | Labyrinth of Debug | fix a broken concurrent pipeline under a hidden checker | 250 |
| 1-8 | `s007-cli-spec` | 3 | The Foundry | build a CLI that matches a spec exactly, incl. exit codes | 200 |
| 1-9 | `s010-codemod-migration` | 6 | The Summit | migrate a codebase from a legacy API to a v2 SDK | 350 |
| 1-10 | `s009-tests-that-test` | 5 | Spire of Systems | write tests that kill injected mutants | 300 |

The archived World 1 pilot cleared every stage on the first try. World 1 now
starts with bounded edits and a log lookup. It ends with migrating several
modules to a new SDK and designing tests that catch injected faults. The latter
two used the most tokens in that pilot.

The ten Summit routing levels add one switch and one rule per level. Each
retains the prior rules and grades independently on a fresh workspace. A hidden
graph makes every switch configuration reachable at the start node. That
portion of the state space doubles at each step, from 2 configurations to 1,024.

| Level | Added rule | Reachable switch configurations |
| --- | --- | ---: |
| 2-1 | Toggle switches and satisfy arrival requirements | 2 |
| 2-2 | Gates that require a switch to be on | 4 |
| 2-3 | Gates that require a switch to be off | 8 |
| 2-4 | Clear switches | 16 |
| 2-5 | Set switches | 32 |
| 2-6 | Discounts for switches that are on | 64 |
| 2-7 | Exact terminal switch configuration | 128 |
| 2-8 | Discounts for switches that are off | 256 |
| 2-9 | Copy switch values | 512 |
| 2-10 | Swap switch values | 1,024 |

Each level compares the submitted JSON Lines program with an independent
reference on seeded graphs, targeted rule checks, and cases exercising every
switch. The exponential growth is a property of the test instances. Model pass
rates still need calibration. The World 2 pilot cleared all ten on its first
try, so v4 retains the cumulative rule order as its complexity ranking.

Base points are `100 × (1 + 0.5 × (tier − 1))`. Clear multipliers are 1.2, 0.75,
and 0.50 for attempts one through three, with penalties for exceeding the
tool budget. A task keeps its tier and raw value when it moves to a new level
position. A perfect v4 run earns 10,740 points.

The opening level is **1-1**, the Summit begins at **2-1**, and the Deep Works
begins at **3-1**. Each world reports a **score out of 100**. Each stage contributes
its earned points divided by its own first-try maximum, and the world score
averages those shares across its ten levels. For a run ended by ordinary failures, failed and unreached stages
contribute zero. When the test clock interrupts a run, earned raw points and
completed world scores remain visible. The interrupted world has no final
score and later worlds are marked unplayed. For example, five first-try clears at full points earn 50/100
in either half. The original tier-weighted points remain available in the replay.

Every stage ships two **controls**: a `fixed` workspace that must pass the oracle and
an `empty` one that must fail it. A stage whose oracle accepts nothing is not a stage,
so the controls are checked in CI:

```bash
python3 -m engine controls
```


### World 3 · The Deep Works

On board v3, OpenCode with its configured Qwen default cleared eight of ten
independent levels on seed 1. The SDK retrofit and delivery repair cleared
in 36 and 41 seconds. The framing task exhausted its stage clock and the
reporting task failed on multiple JSON Lines inputs. These observations are
from one trial per level. A timeout also depends on the harness and hardware.

| Level | Task | What makes the next part of the world harder |
| --- | --- | --- |
| 3-1 | Instrument Retrofit | Adapt callers to a new sensor interface. |
| 3-2 | Silent Dispatch | Coordinate retries, duplicate orders, and totals across two services. |
| 3-3 | Echo Ledger | Reconcile duplicates and conflicting events independently of arrival order. |
| 3-4 | Archive Bridge | Support reads and safe upgrades across two on-disk formats. |
| 3-5 | Revision Almanac | Answer historical queries across revisions, deletions, and UTC day changes at scale. |
| 3-6 | Transfer Press | Resolve simultaneous rename cycles and publish atomically after validating every batch. |
| 3-7 | Narrow Channel | Parse a fragmented binary stream under backpressure and a memory limit. |
| 3-8 | Shift Exchange | Pause and resume multi-worker jobs across staffing changes, cancellations, and long idle periods. |
| 3-9 | Portfolio Engine | Find an exact optimum under two shared budgets, interacting item values, and tie rules. |
| 3-10 | Commit Furnace | Recover interleaved transactions across restarts, stale writes, and partial or compacted logs. |

The v4 order is provisional. Compare independent first-try and eventual clear
rates on matching seeds across weak, medium, and strong models. Use more seeds
when neighboring levels are tied. Record budget exhaustion separately from
incorrect solutions. The design target is about five independent clears in
World 3 for the OpenCode/Qwen 120B baseline. A stage cleared on a retry counts
as one clear but earns fewer game points.

On seed 1, the same OpenCode default cleared all ten v4 levels. It cleared
nine on the first attempt, including the exact portfolio planner. Journal
recovery passed on the second attempt. The result exceeded the five-clear
target and prompted a separate pilot of harder tasks. Both pilots used one
independent trial per level with the standard clock and retries.

```bash
python3 -m engine run --harness opencode --world 3
python3 -m engine calibrate --harness opencode --world 3 --seed 1 --seed 37
```

Normal play stops when a level exhausts its attempts. Calibration starts each
level independently on each supplied seed, with the standard retry rules
within a level. Repeat a seed to run additional trials on the same inputs.
The report shows clears, first-try passes, decided trials, incompletes, and
invalid trials. Its clear rate divides clears by decided trials (passes and
ordinary failures). For example, five clears, two failures, and three incomplete
trials give 5/7 decided, with 7/10 coverage. A run with only incompletes has
no clear rate. An infrastructure or integrity error also withholds the aggregate
rate. Difficulty groups compare only levels with decided results on every
requested trial, ordering by eventual clears and then first-try passes.
Calibration records are stored separately from sequential runs in Results.

**Deadline grading (run schema 3).** The stage clock limits how long the harness
can work. At timeout the engine grades a copy of the stopped workspace with
the same checks and seed as a normal submission. A verified pass earns the
normal points for that attempt and unlocks the next level. If the work falls
short, the level is **incomplete** and sequential play stops. Calibration
continues to the next independent trial. The attempt records its timeout
separately from its verdict. Integrity violations and checker errors keep their
own verdicts. Runtime limits on the submitted program inside a level's tests
remain part of that level's requirements.

The OpenCode connector starts a private server for each attempt and stops its
process group at the deadline. Legacy OpenCode sessions could keep editing
after their CLI timed out. Their historical scores use their original rules
and appear in separate comparison groups.

Use the same harness for initial model comparisons. Record local hardware and
use a clock budget that gives the selected local configuration time to generate.
Pilot the 120B-class and frontier baselines before using this board to make
claims about either group.

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
sandbox. These checks cover engine behavior and oracle controls.

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
# stages cleared 30 / 30, points 10740.0, first-try rate 100%
```

CI uses this run to verify a complete playthrough. It is also the cheapest way to get a full board to look at in the viewer.

### With a real harness

Install and authenticate the harness separately, then select it by name. Each
attempt starts at the root of a fresh workspace.

| `--harness` | Executable | Model selection |
| --- | --- | --- |
| `opencode` | `opencode` | OpenCode model ID |
| `cline` | `cline` | `provider/model`, or a model ID for Cline's default provider |
| `kilo` | `kilo` | Kilo `provider/model` |
| `codex` | `codex` | Codex model ID |
| `grokbuild` | `grok` | Grok Build model ID |
| `antigravity` | `agy` or `antigravity` | Antigravity model ID |
| `t3code` | `t3code-threads` | `instance/model` or the configured T3 provider |
| `pi` | `pi` | Pi `provider/model` |
| `hermes` | `hermes` | Model ID on the configured Hermes provider |

```bash
python3 -m engine run --harness codex --limit 1
python3 -m engine run --harness kilo --model provider/model --limit 1
```

T3 Code uses the [t3code-threads client](https://github.com/kcosr/t3code-threads).
Configure it to reach a T3 server running on the benchmark host with access to
the attempt directories. It creates a new thread per attempt and uses T3's
automatic edit-approval mode. Its completion output lacks tool and token
counts, so full T3 runs are replayable and excluded from ranked results.

Hermes uses its one-shot JSON stream and local file and terminal toolsets.
Configure the Hermes profile's terminal cwd as `.` so it starts in the
attempt directory. Pi runs its coding agent with session persistence disabled.
To benchmark a DeepSeek **model**, select it under a configured harness such
as Pi, Kilo, or OpenCode. This records the model together with the tool runner
that actually edits and tests the workspace.

#### Bring your own agent

Use `--harness command --harness-bin /path/to/wrapper` for another local agent,
an SDK, or an ACP client that can run a single turn. The wrapper runs in the
attempt workspace and receives one JSON object on stdin with `prompt`,
`model`, `stage_id`, `attempt`, and `timeout_s`. The wrapper owns provider
authentication and must stop its agent before it exits.

On stdout, emit one JSON object per line. Emit one `tool.call` for each
executed call, with an optional unique `id`, and finish with one `result`
reporting success and total tokens. Use stderr for diagnostics. For example:

```jsonl
{"type":"tool.call","tool":"read","id":"call-1"}
{"type":"result","ok":true,"tokens":145,"text":"Finished"}
```

The engine verifies workspace artifacts after the wrapper exits. Its basename
identifies the command adapter in results.

Useful flags:

| Flag | Meaning |
| --- | --- |
| `--board boards/v1.yaml` | play the original ten-stage board. The default is `boards/v4.yaml`. |
| `--limit N` | play only the first N stages — good for a cheap calibration run |
| `--harness-bin PATH` | override the executable for an adapter. Required for `command`. |
| `--only s006-sessionizer` | one stage, for authoring or debugging |
| `--world 1`, `--world 2`, or `--world 3` | run one world independently. The equivalent stage ranges are `--segment 1-10`, `--segment 11-20`, and `--segment 21-30`. |
| `--seed N` | selects hidden routing and engineering cases in Worlds 2 and 3. World 1 fixtures are static. |
| `--out DIR` | where runs land (default `runs/`) |
| `--quiet` | just the summary, no live event stream |

A sequential run ending incomplete returns exit code 3. A calibration with
incompletes also returns 3 unless an infrastructure or integrity error takes
precedence. The per-stage clock is shared across at most three attempts. Use `--only` to
sample a specific routing level or `--limit` to sample the opening of the board.
For example, `--only s020-swap-relays --seed 37` plays the final level alone.

### What a run leaves behind

```
runs/<run-id>/run.json                 score sheet + replay tape
runs/<run-id>/events.jsonl             every engine event, in order
runs/<run-id>/<stage>/attempt<N>/      the workspace the agent actually had
runs/<run-id>/<stage>/attempt<N>.transcript.json   prompt + raw harness output
runs/index.json                        every run, for the results viewer
```

The viewer takes completed run scores and playback from `run.json` and discovers
runs through `runs/index.json`. During an active run, progress appears in
the terminal. Reload the viewer after the run finishes.

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

This archived run demonstrates one harness-model pairing clearing v1 at seed 1.
All stages cleared on the first try, so the archive contains zero observations
of feedback uptake.

To see it: `python3 -m engine serve`, then open the Results tab and press Replay.

## The viewer

The viewer combines a 3D board, score replay, results table, test catalog, and
connector setup guide.

```bash
cd board
npm install
npm run build            # writes board/dist
cd ..
python3 -m engine serve  # http://localhost:8088/
```

`engine serve` rebuilds `runs/index.json` and serves the built viewer, public test
and connector metadata from `/catalog.json`, and allowlisted run records.

For development, `cd board && npm run dev` gives a hot-reloading server on :5173
that proxies `/runs` and `/catalog.json` to `engine serve` on :8088.

In the app:

- **Board** — the 3D spine. Click a node, or a row in the sidebar, to focus it; the
  three crystals next to a focused node are its three attempts, lit by verdict.
- **Score replay** — the same run as a chart. Press **Replay** and the playhead walks
  the spine while the cumulative score fills in. Speed control and a scrub bar.
- **Results** — completed runs grouped by comparison cohort. Choose **Replay** to
  watch the run on the board.
- **Worlds** — explore each world's layout and inspect its levels directly.
- **Tests** — browse stage tasks, verification methods, scoring, and budgets.
- **How to** — configure built-in adapters, connect a custom wrapper, and load results.

World 1 uses an ascending spiral, World 2 uses a rising zigzag, and World 3
uses forge terraces with copper lift rails and turning gears. Configure
new world ranges in the board YAML and add their path, platform geometry,
and palette to `board/src/worldThemes.js`. The same bot and replay controls
follow the path for every world.

## Adding a stage

1. `stages/<id>/stage.yaml` — brief, tier, budget, and an oracle spec (one of
   `file_exact`, `file_normalized`, `json_equal`, `diff_budget`, `command`, `script`,
   `differential`, `mutation`, `timing`).
2. `stages/<id>/workspace/` — the fixture the agent gets.
3. `stages/<id>/oracle/` — the verification. Never copied into the sandbox, never
   callable by the agent.
4. `stages/<id>/controls/{fixed,empty}` — the two controls.
5. Add the id to the intended board file, then `python3 -m engine validate && python3 -m engine controls`.

Oracle scripts run with the working directory set to the sandbox workspace, so use
cwd-relative paths for agent files and `__file__`-relative paths for hidden fixtures.

## Measurement limits

- The local runner gives agents the operator's filesystem and network access.
  Oracle sources and fixed controls are reachable on the host. Treat local
  results as cooperative measurements until the verifier has an isolation
  boundary.
- The results table ranks full benchmark runs within a board, version, seed,
  and record schema. Controls, partial runs, archives, infrastructure errors,
  and integrity violations are available for replay.
- A result describes a harness and model together. Use an explicit model
  identifier and control provider and harness settings across runs. One archived run cannot establish model or harness
  rankings.
- Token totals reflect completed usage reports and can be incomplete, including
  on timeouts. Hard token ceilings, a whole-run cap, and a reference speed
  median remain unimplemented.

## Layout

```
DESIGN.md              the design record — start here
AGENTS.md              rules for agents working in this repo
SECURITY.md            secret-handling policy
boards/v1.yaml         the original ten-stage spine
boards/v2.yaml         the twenty-stage board
boards/v3.yaml         the original World 3 pilot board
boards/v4.yaml         the current thirty-stage difficulty order
stages/                stage definitions: workspace, oracle, controls
engine/                orchestrator, oracles, sandbox, harness adapters, CLI
engine/harness/        native adapters, command adapter, and controls
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

## License

[MIT](LICENSE).
