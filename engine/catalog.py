"""Public viewer metadata. Keep checker inputs and expected outputs out of this payload."""

from .harness import REGISTRY

TASKS = {
    "s001-exact-edit": (
        "Apply three specified edits to meeting notes.",
        "Compare the resulting notes to a normalized reference and cap the number of changed lines.",
    ),
    "s002-json-repair": (
        "Repair a hand-edited JSON configuration while preserving its intended values.",
        "Parse the file, compare its JSON structure and value types to the reference, and enforce a changed-line limit.",
    ),
    "s003-rename-symbol": (
        "Rename an exported function across its definition, callers, and tests.",
        "Run the project suite, check that the old name and compatibility aliases are gone, and cap the changed lines.",
    ),
    "s004-offbyone": (
        "Repair a catalogue module's boundary errors while preserving the public API.",
        "Exercise catalogue operations on hidden boundary cases and enforce a changed-line limit.",
    ),
    "s005-log-search": (
        "Summarize errors and latency from a fixed proxy log.",
        "Parse the submitted JSON report and compare its counts, tie-breaking, and latency fields to reference values. The source log is protected.",
    ),
    "s006-sessionizer": (
        "Build a command-line filter that groups access-log requests into sessions and emits CSV.",
        "Run the filter on unseen logs and compare the CSV to reference outputs covering gaps, malformed lines, and multiple clients.",
    ),
    "s007-cli-spec": (
        "Build a persistent budget CLI for adding, spending, balancing, and reporting money.",
        "Run commands against temporary ledgers and check exact money arithmetic, reports, stored entries, and error behavior.",
    ),
    "s008-pipeline-fix": (
        "Fix a task pipeline's queue, shutdown, retry, and aggregation bugs.",
        "Run hidden suites covering queue ordering and concurrency, worker retry and error handling, and report aggregation.",
    ),
    "s009-tests-that-test": (
        "Write a test suite for a pricing module.",
        "Require the suite to pass on the protected original, then rerun it against individually mutated copies and measure the share of bugs it catches.",
    ),
    "s010-codemod-migration": (
        "Migrate a service to a new messaging SDK and configuration format.",
        "Run hidden checks for config conversion, publishing and retry semantics, and migration hygiene.",
    ),
    "s021-ledger-replay": (
        "Rebuild account balances from a ledger that may repeat events or contain conflicting copies.",
        "Shuffle seeded ledgers and verify that repeats count once and every conflicting ID is discarded.",
    ),
    "s022-storage-compat": (
        "Upgrade a file format while keeping the original CLI usable with both formats.",
        "Run the CLI repeatedly on old, current, and invalid files. Compare account totals, entry order, and files that should stay untouched.",
    ),
    "s023-late-event-report": (
        "Rebuild daily reports when corrections and deletions arrive late.",
        "Shuffle revisions and timestamp offsets, then compare the corrected totals by UTC calendar day.",
    ),
    "s024-stream-framing": (
        "Read length-prefixed records from a binary stream and emit each result as soon as it arrives.",
        "Test fragmented input, malformed records, and a stream larger than the program's memory allowance.",
    ),
    "s025-safe-migration": (
        "Convert a file safely when the migration can stop partway through.",
        "Simulate interruptions at every record boundary, check the original and destination, then retry and compare the finished output.",
    ),
    "s026-scheduler": (
        "Schedule dependent jobs on a fixed number of workers while handling cancellations.",
        "Compare ordered event traces for simultaneous cancellation and completion, chained dependencies, and priority rules.",
    ),
    "s027-resource-planner": (
        "Choose the best set of items under a budget, dependencies, and incompatible choices.",
        "Exhaustively solve small cases and verify finishable larger cases with known optima and deterministic tie-breaking.",
    ),
    "s028-sdk-compat": (
        "Migrate several modules to a new sensor SDK while preserving their public interfaces.",
        "Check public signatures and legacy imports, then exercise missing values, offline sensors, unit conversion, and request order.",
    ),
    "s029-delivery-regression": (
        "Repair order intake, delivery retries, and totals after a simulated incident.",
        "Replay seeded delivery scenarios and compare deduplication, exact gateway calls, rejection handling, and customer totals.",
    ),
    "s030-pipeline-recovery": (
        "Recover an interrupted event pipeline and migrate its checkpoints.",
        "Restart at successive checkpoint boundaries, replay revisions and deletions, and verify idempotence and handling of appended input.",
    ),
    "s031-time-report": (
        "Answer what a daily report would have shown at a particular point in the arrival history.",
        "Compare answers at every prefix of small shuffled histories and at thousands of out-of-order cutoffs in a larger ledger. Corrections can move records between UTC days.",
    ),
    "s032-batch-migration": (
        "Rename stored records in batches, including swaps, and publish the converted file atomically.",
        "Interrupt and retry conversions, introduce an invalid late batch, and check that readers holding the old file still see its original bytes.",
    ),
    "s033-crew-scheduler": (
        "Keep jobs moving through staffing changes. A job can pause, resume, or lose a prerequisite while it waits.",
        "Compare the event trace to a tick-by-tick simulation, then stretch the gaps between events and check that the order and timing still agree.",
    ),
    "s034-bundle-planner": (
        "Select the most valuable compatible portfolio that fits both the spending limit and the space available. Pairs of items can earn a bonus or a penalty.",
        "Check every possible selection on small inputs. Independently solve 48-item portfolios where groups compete for both budgets and ties have a defined winner.",
    ),
    "s035-journal-recovery": (
        "Recover several clients’ overlapping transactions after a restart, including when part of the journal has already been archived.",
        "Restart at each record boundary. Verify pending writes, conflict rollback, deletions, old checkpoints, and recovery when the last record arrives in pieces.",
    ),
    "s036-versioned-wiring": (
        "Inspect old versions of a wiring diagram to tell whether two sensors agree, disagree, or have contradictory wiring.",
        "Rebuild small diagrams independently for each query, then check thousands of branches that cut, replace, or contradict a wire in a long chain.",
    ),
    "s037-sensor-constraints": (
        "Predict a sensor reading from another sensor in any saved version of a network. A loop can fix a reading or make the entire set of equations inconsistent.",
        "Propagate readings directly through small graphs and verify predictions on a large branching history with known transformations.",
    ),
    "s038-probe-policy": (
        "Choose the least expensive way to diagnose a device when the test itself can change the device and the same signal can have several causes.",
        "Compare the worst-case cost and every optimal first probe against successively longer diagnostic plans. Include devices that can never be diagnosed.",
    ),
    "s039-noisy-diagnosis": (
        "Guarantee a diagnosis and a safe stop when some readings may be wrong and the device hides the cost of each test.",
        "Price every possible path on small devices, then test cases where two devices incur their highest costs at different times or require repeated measurements.",
    ),
    "s040-frontier-portfolio": (
        "Choose an optimal assembly plan across groups that share parts. Report how many plans tie and which parts every winning plan needs.",
        "Enumerate small portfolios independently. Larger cases have shared parts and billions of tied choices with a known count and intersection.",
    ),
    "s041-branch-reports": (
        "Answer date-range reports across a branching ledger where a price change can revalue thousands of existing rows.",
        "Rebuild small ledgers directly, then compare a large forked history to sums derived independently from its transactions and rates.",
    ),
    "s042-station-recovery": (
        "Commission a diagnostic station whose tests and costs depend on past wiring readings. Faulty wiring can take an entire probe offline.",
        "Exercise both services independently, then compare the integrated station’s disabled probes and guaranteed diagnoses with exhaustive small-device trials.",
    ),
}

ROUTING_RULES = {
    "s011-toggle-routing": (
        "gates",
        "Find the cheapest route that leaves the required switches on. Some roads flip a switch when you take them.",
        "The grader checks whether your answer tracks the switches you flipped along the way, even if you revisit a place.",
    ),
    "s012-live-gates": (
        "gates",
        "Some roads open only when a particular switch is on.",
        "The grader looks for routes that pay to turn on a switch before taking a shortcut that was closed at the start.",
    ),
    "s013-dark-gates": (
        "gates",
        "Some roads work the other way around. They open only when a particular switch is off.",
        "The grader catches answers that take a cheap road after an earlier move has turned its switch on and closed it.",
    ),
    "s014-reset-routing": (
        "gates",
        "Some roads turn a switch off whenever you cross them.",
        "The grader checks whether taking a detour to turn off a switch can reopen a road and make an otherwise blocked trip possible.",
    ),
    "s015-latching-relays": (
        "gates",
        "Some roads turn a switch on and leave it on if it was already on.",
        "The grader checks that turning the same switch on twice leaves it on. Flipping it twice would leave it off.",
    ),
    "s016-live-tolls": (
        "prices",
        "An on switch can make a road cheaper to cross.",
        "The grader checks whether you compare the cost of turning on a switch with the savings it unlocks. A discount can take a road's price down to zero.",
    ),
    "s017-terminal-state": (
        "prices",
        "Finishing can require an exact switch pattern. The listed switches must be on and every other switch must be off.",
        "The grader includes trips where reaching the right place is only the first step. The trip ends once the switches also match.",
    ),
    "s018-dark-tolls": (
        "prices",
        "An off switch can now earn a discount too.",
        "The grader compares routes where leaving a switch off saves more than turning it on. If several discounts apply to the same road, they add up.",
    ),
    "s019-copy-relays": (
        "signals",
        "Some roads copy one switch's setting to another. The original switch keeps its setting.",
        "The grader checks that the new switch takes the original's value and can then open a different gate.",
    ),
    "s020-swap-relays": (
        "signals",
        "Some roads exchange the settings of two switches. Several switch changes can happen on the same crossing.",
        "The grader checks that both switches get the other's previous setting and that swaps happen after copying. A later gate may require one switch on and the other off.",
    ),
}

CONNECTORS = {
    "opencode": ("OpenCode", "opencode", "Run each attempt with a private server and an in-memory session database. Read tool events and per-step token usage, and stop workers at the stage deadline.", "Configure the provider in OpenCode's config or environment. Model format: provider/model."),
    "cline": ("Cline", "cline", "Start a local one-shot JSONL session with a private data directory. Read tool events and cumulative usage where emitted.", "Authenticate in Cline. Use provider/model or a model ID on Cline's default provider."),
    "kilo": ("Kilo Code", "kilo", "Run the prompt in a private local runtime with the shared daemon disabled. Read tool and step events from JSONL.", "Configure a Kilo provider and its autonomous permissions. Model format: provider/model."),
    "codex": ("Codex CLI", "codex", "Run an ephemeral codex exec session with workspace-write access. Read JSONL tool items and turn usage.", "Authenticate in Codex. Pass a Codex model ID or use its configured default."),
    "grokbuild": ("Grok Build", "grok", "Run a single prompt with cross-session memory disabled. Read streaming tool events and usage.", "Authenticate in Grok Build. Pass a Grok Build model ID or use its configured default."),
    "antigravity": ("Antigravity CLI", "agy or antigravity", "Run print mode with the CLI sandbox enabled. Count distinct tool steps and read terminal usage.", "Authenticate in the Antigravity CLI. Pass an Antigravity model ID or use its configured default."),
    "t3code": ("T3 Code", "t3code-threads", "Run a fresh thread on a disposable loopback server and stop its workers. Runs are replayable and unranked because the client omits tool counts.", "Install t3 and t3code-threads locally. Each attempt starts its own server. Use instance/model or the default provider."),
    "hermes": ("Hermes", "hermes", "Start a one-shot JSONL chat with the local file and terminal toolsets.", "Configure a provider and set terminal.cwd to . in the Hermes profile. Use a model ID for that provider."),
    "pi": ("Pi", "pi", "Launch JSON mode with session persistence disabled. Read tool execution events and assistant-message usage.", "Configure a Pi provider. Model format: provider/model."),
    "command": ("Custom command", "Operator-supplied executable", "Read the request from stdin and emit tool calls and one terminal JSONL result to stdout.", "Pass --harness-bin PATH. The wrapper owns authentication and must cancel any external work on disconnect."),
    "fake": ("Fake control", "Built into the engine", "Run scripted behavior used to test the benchmark plumbing.", "No provider account or external executable required."),
    "solve": ("Solve control", "Built into the engine", "Install each stage's known-good control fixture to verify the full playthrough.", "No provider account or external executable required."),
}


def stage_entry(stage, world_level):
    description, measurement = TASKS.get(stage.id, (None, None))
    routing_group = None
    if stage.id in ROUTING_RULES:
        routing_group, description, measurement = ROUTING_RULES[stage.id]
    checks = []
    for spec in stage.oracles:
        entry = {"kind": spec.kind}
        if spec.kind == "diff_budget":
            entry["maxChangedLines"] = spec.config.get("max_changed_lines", 0)
        if spec.kind == "mutation":
            entry["minKillRate"] = spec.config.get("min_kill_rate", 0.6)
            entry["mutantCount"] = len(spec.config["mutants"])
        checks.append(entry)
    return {
        "id": stage.id, "name": stage.name, "tier": stage.tier, "region": stage.region,
        "description": description, "measurement": measurement, "checks": checks,
        "capabilities": stage.capabilities, "attempts": stage.attempts,
        "seconds": stage.timeout_s, "toolBudget": stage.tool_budget, "basePoints": stage.value(),
        "seeded": stage.seedable, "routingGroup": routing_group, **world_level,
    }


def public_catalog(board):
    connectors = []
    for key in REGISTRY:
        label, executable, wiring, setup = CONNECTORS[key]
        connectors.append({
            "id": key, "label": label, "executable": executable,
            "wiring": wiring, "setup": setup,
        })
    return {
        "board": {"id": board.id, "version": board.version,
                  "stages": [stage_entry(stage, board.world_level(i))
                             for i, stage in enumerate(board.stages, start=1)]},
        "connectors": connectors,
    }
