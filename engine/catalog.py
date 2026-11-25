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
    "opencode": ("OpenCode", "opencode", "Run in autonomous JSONL mode. Read tool events and per-step token usage.", "Sign in or configure a provider in OpenCode. Model format: provider/model."),
    "cline": ("Cline", "cline", "Start a local one-shot JSONL session. Read tool events and cumulative usage where emitted.", "Authenticate in Cline. Use provider/model or a model ID on Cline's default provider."),
    "kilo": ("Kilo Code", "kilo", "Pipe the prompt into an autonomous run. Read tool and step events from JSONL.", "Configure a Kilo provider and its autonomous permissions. Model format: provider/model."),
    "codex": ("Codex CLI", "codex", "Run an ephemeral codex exec session with workspace-write access. Read JSONL tool items and turn usage.", "Authenticate in Codex. Pass a Codex model ID or use its configured default."),
    "grokbuild": ("Grok Build", "grok", "Run a single prompt with cross-session memory disabled. Read streaming tool events and usage.", "Authenticate in Grok Build. Pass a Grok Build model ID or use its configured default."),
    "antigravity": ("Antigravity CLI", "agy or antigravity", "Run print mode with the CLI sandbox enabled. Count distinct tool steps and read terminal usage.", "Authenticate in the Antigravity CLI. Pass an Antigravity model ID or use its configured default."),
    "t3code": ("T3 Code", "t3code-threads", "Create a fresh thread, send the prompt, and stop the provider session. Runs are replayable and unranked because the client omits tool counts.", "Connect t3code-threads to a T3 server with access to the same workspace. Use instance/model or the configured T3 provider."),
    "hermes": ("Hermes", "hermes", "Start a one-shot JSONL chat with the local file and terminal toolsets.", "Configure a provider and set terminal.cwd to . in the Hermes profile. Use a model ID for that provider."),
    "pi": ("Pi", "pi", "Launch JSON mode with session persistence disabled. Read tool execution events and assistant-message usage.", "Configure a Pi provider. Model format: provider/model."),
    "command": ("Custom command", "Operator-supplied executable", "Read the request from stdin and emit tool calls and one terminal JSONL result to stdout.", "Pass --harness-bin PATH. The wrapper handles authentication and agent shutdown."),
    "fake": ("Fake control", "Built into the engine", "Run scripted behavior used to test the benchmark plumbing.", "No provider account or external executable required."),
    "solve": ("Solve control", "Built into the engine", "Install each stage's known-good control fixture to verify the full playthrough.", "No provider account or external executable required."),
}


def stage_entry(stage):
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
        "seeded": stage.seedable, "routingGroup": routing_group,
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
                  "stages": [stage_entry(stage) for stage in board.stages]},
        "connectors": connectors,
    }
