"""Command line interface.

    python3 -m engine validate          check every stage definition
    python3 -m engine controls          prove each stage's controls behave
    python3 -m engine run               play the board with a harness
    python3 -m engine report            print a run summary
    python3 -m engine index             rebuild runs/index.json for the viewer
    python3 -m engine serve             serve the board and results viewer
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from . import harness as harness_mod
from . import oracles as oracle_mod
from .catalog import public_catalog
from .orchestrator import Orchestrator, RunConfig
from .runrecord import RunRecord
from .sandbox import Sandbox
from .spec import Board, SpecError, load_board

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BOARD = ROOT / "boards" / "v2.yaml"


def _board(args) -> Board:
    return load_board(Path(args.board))


def cmd_validate(args) -> int:
    try:
        board = _board(args)
    except SpecError as exc:
        print(f"BOARD INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"board {board.id} v{board.version} — {board.size} stages")
    width = max(len(s.id) for s in board.stages)
    for stage in board.stages:
        kinds = ", ".join(o.kind for o in stage.oracles)
        print(f"  {stage.id:<{width}}  tier {stage.tier}  {stage.value():>4} pts  "
              f"[{kinds}]")
    print("all stage definitions valid")
    return 0


def _control_box(stage, control: str, seed: int) -> Sandbox:
    """A sandbox whose workspace is a control fixture instead of the fixture."""
    tmp = Path(tempfile.mkdtemp(prefix="agentic-control-"))
    try:
        shutil.copytree(stage.workspace, tmp / "_original")
        shutil.copytree(stage.path / "controls" / control, tmp / "workspace")
    except FileNotFoundError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SpecError(f"{stage.id}: missing controls/{control}: {exc}") from exc
    box = Sandbox(tmp, tmp / "_original", stage.protected)
    box.oracle_dir = stage.oracle_dir
    box.oracle_seed = seed if stage.seedable else None
    return box


def cmd_controls(args) -> int:
    """Every stage ships two controls. A no-op that must pass proves the stage is
    solvable and the oracle is not impossible. A do-nothing that must fail proves
    the oracle is not vacuous. A stage that passes for a do-nothing agent is
    broken, and this command is what catches it."""
    board = _board(args)
    failures = 0
    for stage in board.stages:
        results = []
        for control, expect_pass in (("fixed", True), ("empty", False)):
            if not (stage.path / "controls" / control).is_dir():
                print(f"  {stage.id}: MISSING controls/{control}")
                failures += 1
                continue
            box = _control_box(stage, control, args.seed)
            try:
                matches_fixture = control != "empty" or not box.delta().touched
                checks = []
                for spec in stage.oracles:
                    checks += oracle_mod.build(spec).run(box)
                error = not checks or any(c.name.endswith((":error", ":timeout")) for c in checks)
                ok = all(c.ok for c in checks)
                good = not error and matches_fixture and ok == expect_pass
                results.append(good)
                if not good:
                    failures += 1
                    bad = [c.name for c in checks if not c.ok]
                    reason = ("empty control differs from workspace" if not matches_fixture else
                              "checker error" if error else
                              f"expected {'pass' if expect_pass else 'fail'}")
                    print(f"  {stage.id}: control {control}: {reason}"
                          + (f" (failing: {', '.join(bad[:4])})" if bad else ""))
            finally:
                shutil.rmtree(box.root, ignore_errors=True)
        if all(results) and results:
            print(f"  {stage.id}: controls behave (fixed passes, empty fails)")
    if failures:
        print(f"\n{failures} control problem(s) — those stages are not trustworthy")
        return 1
    print("\nall controls behave")
    return 0


def cmd_run(args) -> int:
    board = _board(args)
    adapter = harness_mod.create(args.harness, model=args.model, **(
        {"bin_path": args.harness_bin} if args.harness_bin else {}
    ))
    harness_name = f"command:{Path(args.harness_bin).name}" if args.harness == "command" and args.harness_bin else args.harness
    usable, why = adapter.available()
    if not usable:
        print(f"harness {args.harness!r} unavailable: {why}", file=sys.stderr)
        return 2

    config = RunConfig(board=board, harness=harness_name, model=args.model,
                       seed=args.seed, out_dir=Path(args.out), limit=args.limit,
                       only=args.only, run_id=args.run_id)
    verbose = not args.quiet

    def show(event: dict) -> None:
        if not verbose:
            return
        kind = event["event"]
        if kind == "stage.entered":
            print(f"\n[{event['index']}/{board.size}] {event['stage']} — {event['name']}"
                  f"  (tier {event['tier']})")
        elif kind == "attempt.started":
            print(f"    attempt {event['attempt']} …", flush=True)
        elif kind == "attempt.ended":
            mark = "PASS" if event["verdict"] == "pass" else event["verdict"].upper()
            extra = "" if event["verdict"] == "pass" else \
                f"  failed: {', '.join(event['failed'][:3])}"
            print(f"    attempt {event['attempt']}: {mark}  "
                  f"tools={event['tools']} {event['seconds']}s{extra}")
        elif kind == "stage.cleared":
            print(f"    cleared  +{event['points']} pts")
        elif kind == "stage.failed":
            print(f"    STAGE FAILED after {event['attempts']} attempt(s) — run over")
        elif kind == "run.ended":
            print(f"\nrun ended: stage {event['stageReached']}/{board.size} reached, "
                  f"{event['points']} points")

    started = time.monotonic()
    orchestrator = Orchestrator(config, adapter, on_event=show)
    print(f"run {orchestrator.run_id}  harness={args.harness}  "
          f"model={getattr(adapter, 'label', lambda: args.model)()}  "
          f"board={board.id} v{board.version}")
    record = orchestrator.run()
    print(f"\nsaved {orchestrator.run_dir / 'run.json'}  ({time.monotonic() - started:.0f}s)")
    print_summary(record)
    write_index(Path(args.out))
    if record.status == "infrastructure_error":
        return 2
    return 0 if record.stage_reached == record.selected_stages else 1


def print_summary(record: RunRecord) -> None:
    print("\n" + "=" * 68)
    print(f"  {record.harness} / {record.model}")
    print(f"  board {record.board} v{record.board_version}   seed {record.seed}   {record.status}")
    print("-" * 68)
    for row in record.cumulative_score():
        mark = "PASS" if row["cleared"] else "FAIL"
        print(f"  {row['index']:>2}. {row['stage']:<26} {mark:<4} "
              f"att {row['attempts']}  +{row['points']:>6}  "
              f"total {row['cumulative']:>7}")
    final = record.as_dict()["final"]
    print("-" * 68)
    print(f"  stage reached   {final['stageReached']} / {final['boardSize']}")
    print(f"  points          {final['points']}")
    print(f"  first-try rate  {final['firstTryRate']:.0%}")
    trials = final["feedbackTrials"]
    uptake = f"{final['feedbackUptake']:.0%} ({trials} retries)" if trials else "—"
    print(f"  feedback uptake {uptake}")
    attempts = [attempt for stage in record.stages for attempt in stage.attempts]
    tools = final["tool_calls"] if all(a.tools_reported for a in attempts) else "incomplete"
    tokens = final["tokens"] if all(a.tokens_reported for a in attempts) else "incomplete"
    print(f"  tools {tools}   seconds {final['seconds']}   tokens {tokens}")
    print("=" * 68)


def cmd_report(args) -> int:
    path = Path(args.run) / "run.json" if Path(args.run).is_dir() else Path(args.run)
    if not path.exists():
        print(f"no run record at {path}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(data["final"], indent=2))
    for row in data["timeline"]:
        mark = "PASS" if row["cleared"] else "FAIL"
        print(f"  {row['index']:>2}. {row['stage']:<26} {mark:<4} att {row['attempts']} "
              f"+{row['points']:>6} total {row['cumulative']:>7}")
    return 0


def write_index(out_dir: Path) -> Path:
    """Aggregate every run into runs/index.json — the results viewer's data."""
    out_dir = Path(out_dir)
    entries = []
    for record_path in sorted(out_dir.glob("*/run.json")):
        try:
            data = json.loads(record_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        final = data.get("final", {})
        attempts = [attempt for stage in data.get("stages", [])
                    for attempt in stage.get("attempts", [])]
        entries.append({
            "run": data.get("run"),
            "harness": data.get("harness"),
            "model": data.get("model"),
            "board": data.get("board"),
            "boardVersion": data.get("board_version"),
            "schema": data.get("schema", 1),
            "status": data.get("status", "archive"),
            "seed": data.get("seed"),
            "started": data.get("started"),
            "path": f"{record_path.parent.name}/run.json",
            "stageReached": final.get("stageReached", 0),
            "boardSize": final.get("boardSize", 0),
            "points": final.get("points", 0),
            "firstTryRate": final.get("firstTryRate", 0),
            "feedbackUptake": final.get("feedbackUptake", 0),
            "feedbackTrials": final.get("feedbackTrials", 0),
            "toolCalls": final.get("tool_calls", 0),
            "toolsReported": all(a.get("tools_reported", True) for a in attempts),
            "seconds": final.get("seconds", 0),
            "tokens": final.get("tokens", 0),
            "tokensReported": all(a.get("tokens_reported", True) for a in attempts),
            "stoppedAt": final.get("stoppedAt"),
            "timeline": data.get("timeline", []),
        })
    entries.sort(key=lambda e: (e["stageReached"], e["points"]), reverse=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "index.json"
    target.write_text(json.dumps({"generated": time.time(), "runs": entries}, indent=2),
                      encoding="utf-8")
    return target


def cmd_index(args) -> int:
    target = write_index(Path(args.out))
    data = json.loads(target.read_text(encoding="utf-8"))
    print(f"{len(data['runs'])} run(s) indexed -> {target}")
    for entry in data["runs"]:
        print(f"  {entry['harness']:<10} {str(entry['model']):<28} "
              f"stage {entry['stageReached']}/{entry['boardSize']}  "
              f"{entry['points']:>7} pts  first-try {entry['firstTryRate']:.0%}")
    return 0


def cmd_serve(args) -> int:
    """Serve the built viewer and the run data, and nothing else.

    Expose viewer assets, the public catalog, and allowlisted run artifacts.
    """
    import http.server
    import io
    import posixpath
    import socketserver
    import urllib.parse

    out = Path(args.out).resolve()
    write_index(out)
    dist = ROOT / "board" / "dist"
    if not (dist / "index.html").exists():
        print("viewer is not built yet:\n"
              "  cd board && npm install && npm run build", file=sys.stderr)
        return 1

    catalog = json.dumps(public_catalog(_board(args))).encode("utf-8")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def send_head(self):
            if urllib.parse.urlsplit(self.path).path == "/catalog.json":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(catalog)))
                self.end_headers()
                return io.BytesIO(catalog)
            return super().send_head()

        def translate_path(self, path):
            raw = urllib.parse.urlsplit(path).path
            rel = posixpath.normpath(urllib.parse.unquote(raw)).lstrip("/")
            head, _, rest = rel.partition("/")
            if rel in ("", "."):
                target = dist / "index.html"
            elif head == "board" and (rest == "dist" or rest.startswith("dist/")):
                target = dist / rest[len("dist"):].lstrip("/")
            elif head == "assets":
                # the built index.html is served at "/" and references ./assets
                target = dist / "assets" / rest
            elif head == "runs":
                parts = rest.split("/")
                if rest != "index.json" and (
                    len(parts) != 2 or parts[0].startswith(".")
                    or parts[1] not in {"run.json", "events.jsonl"}
                ):
                    return ""
                target = out / rest
                return str(target) if target.resolve() == target and target.is_file() else ""
            else:
                return ""
            target = target.resolve()
            return str(target) if target.is_relative_to(dist.resolve()) and target.is_file() else ""

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", args.port), Handler) as httpd:
        print(f"board + results viewer on http://localhost:{args.port}/")
        print(f"run data from {out}")
        print("control-C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engine", description="Agentic Board")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--board", default=str(DEFAULT_BOARD))
        p.add_argument("--out", default=str(ROOT / "runs"))

    p = sub.add_parser("validate", help="check stage definitions")
    common(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("controls", help="verify each stage's controls")
    common(p)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(func=cmd_controls)

    p = sub.add_parser("run", help="play the board")
    common(p)
    p.add_argument("--harness", default="opencode", choices=sorted(harness_mod.REGISTRY))
    p.add_argument("--model", default=None)
    p.add_argument("--harness-bin", help="override the adapter executable; required for command")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--limit", type=int, default=None, help="play only the first N stages")
    p.add_argument("--only", default=None, help="play a single stage by id")
    p.add_argument("--run-id", default=None)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="print a run summary")
    p.add_argument("run")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("index", help="rebuild runs/index.json")
    common(p)
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("serve", help="serve the board and results viewer")
    common(p)
    p.add_argument("--port", type=int, default=8088)
    p.set_defaults(func=cmd_serve)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SpecError as exc:
        print(f"invalid spec: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
