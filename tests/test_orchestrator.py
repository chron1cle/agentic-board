"""End-to-end game loop against the fake harness.

These are the tests that say the instrument measures what it claims to: a fresh
workspace per attempt, the ledger carried between attempts, three failures
ending the run, and the run record describing all of it.
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from engine.feedback import (VERDICT_BUDGET, VERDICT_ERROR, VERDICT_FAIL,
                             VERDICT_INTEGRITY, VERDICT_PASS)
from engine.harness.base import HarnessRequest
from engine.harness.fake import FakeHarness
from engine.harness.solve import SolveHarness
from engine.orchestrator import Orchestrator, RunConfig
from engine.spec import SpecError, load_board

ROOT = Path(__file__).resolve().parent.parent
BOARDS = ROOT / "boards"
STAGES = ROOT / "stages"

# What a correct agent produces, read from the stage's own answer key so the
# test can never drift from the oracle it is testing against.
CORRECT = (STAGES / "s001-exact-edit" / "oracle" / "key" / "meeting.md").read_text()
MANIFEST = (STAGES / "s002-json-repair" / "oracle" / "key" / "app.json").read_text()


class HarnessCase(unittest.TestCase):
    def play(self, script, board="smoke.yaml", default="noop", **config_kw):
        self.tmp = Path(tempfile.mkdtemp(prefix="orch-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        board_obj = load_board(BOARDS / board)
        config = RunConfig(board=board_obj, harness="fake", out_dir=self.tmp / "runs",
                           run_id="testrun", **config_kw)
        harness = FakeHarness(script, model="fake-model", default=default)
        self.harness = harness
        self.orch = Orchestrator(config, harness)
        events = []
        self.orch.on_event = events.append
        self.events = events
        return self.orch.run()


class ClearingTest(HarnessCase):
    def test_first_try_clear_passes_and_scores(self):
        record = self.play({"s001-exact-edit": [{"write": {"notes/meeting.md": CORRECT}}]})
        self.assertEqual(record.stage_reached, 1)
        self.assertEqual(record.stopped_at, "complete")
        self.assertEqual(record.stages[0].attempts_used, 1)
        self.assertGreater(record.points, 100)
        self.assertEqual(record.first_try_rate, 1.0)

    def test_run_record_and_events_are_written(self):
        self.play({"s001-exact-edit": [{"write": {"notes/meeting.md": CORRECT}}]})
        run_dir = self.tmp / "runs" / "testrun"
        data = json.loads((run_dir / "run.json").read_text())
        self.assertEqual(data["final"]["stageReached"], 1)
        events = [json.loads(line) for line in
                  (run_dir / "events.jsonl").read_text().splitlines()]
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "run.started")
        self.assertEqual(kinds[-1], "run.ended")
        self.assertIn("stage.cleared", kinds)

    def test_transcript_is_kept_per_attempt(self):
        self.play({"s001-exact-edit": [{"write": {"notes/meeting.md": CORRECT}}]})
        path = self.tmp / "runs" / "testrun" / "s001-exact-edit" / "attempt1.transcript.json"
        transcript = json.loads(path.read_text())
        self.assertIn("<task>", transcript["prompt"])
        self.assertEqual(transcript["tool_calls"], 1)


class FailingTest(HarnessCase):
    def test_doing_nothing_fails_the_stage_and_ends_the_run(self):
        record = self.play({})
        self.assertEqual(record.stage_reached, 0)
        self.assertEqual(record.points, 0.0)
        self.assertEqual(len(self.harness.calls), 3)
        self.assertEqual(record.stages[0].attempts_used, 3)

    def test_every_attempt_gets_a_pristine_workspace(self):
        """A half-edit left by attempt 1 must not still be there in attempt 2."""
        calls = {"n": 0}

        def break_then_something(request):
            calls["n"] += 1
            (request.workspace / "notes" / "meeting.md").write_text("wrecked")

        record = self.play({"s001-exact-edit": break_then_something})
        self.assertEqual(calls["n"], 3)
        self.assertFalse(record.stages[0].cleared)
        # three identical starting points, so three identical fingerprints
        self.assertEqual(len({c.workspace for c in self.harness.calls}), 3)

    def test_the_ledger_reaches_attempt_two(self):
        def fix_on_second(request):
            if request.attempt >= 2:
                (request.workspace / "notes" / "meeting.md").write_text(CORRECT)

        record = self.play({"s001-exact-edit": fix_on_second})
        self.assertTrue(record.stages[0].cleared)
        self.assertEqual(record.stages[0].attempts_used, 2)
        self.assertEqual(record.feedback_uptake, 1.0)
        self.assertLess(record.points, 120.0)
        second_prompt = self.harness.calls[1].prompt
        self.assertIn("prior_attempts", second_prompt)
        self.assertIn("Attempt 1", second_prompt)
        self.assertNotIn(CORRECT.strip().splitlines()[-1], second_prompt)

    def test_first_attempt_prompt_has_no_ledger(self):
        self.play({})
        self.assertNotIn("prior_attempts", self.harness.calls[0].prompt)


class IntegrityTest(HarnessCase):
    def test_touching_a_protected_file_disqualifies(self):
        def tamper(request):
            (request.workspace / "logs" / "app.log").write_text("tampered")

        record = self.play({"s005-log-search": tamper}, board="integrity.yaml")
        stage = record.stages[0]
        self.assertTrue(stage.integrity_violation)
        self.assertFalse(stage.cleared)
        self.assertEqual(stage.attempts[0].verdict, VERDICT_INTEGRITY)
        self.assertEqual(len(stage.attempts), 1)
        self.assertEqual(record.status, VERDICT_INTEGRITY)


class InfrastructureTest(unittest.TestCase):
    def test_a_harness_error_voids_an_attempt_with_a_correct_artifact(self):
        class FailedHarness(FakeHarness):
            def run(self, request):
                result = super().run(request)
                result.exit_code = 1
                return result

        with tempfile.TemporaryDirectory() as tmp:
            board = load_board(BOARDS / "smoke.yaml")
            config = RunConfig(board=board, out_dir=Path(tmp))
            adapter = FailedHarness({"s001-exact-edit": [{"write": {"notes/meeting.md": CORRECT}}]})
            record = Orchestrator(config, adapter).run()
        self.assertEqual(record.status, VERDICT_ERROR)
        self.assertEqual(record.points, 0)
        self.assertEqual(len(adapter.calls), 1)


class MultiStageTest(HarnessCase):
    def test_a_locked_door_stops_the_run(self):
        record = self.play({}, board="two.yaml")
        self.assertEqual(len(record.stages), 1)
        self.assertTrue(any("not played" in note for note in record.notes))

    def test_passing_both_stages_plays_the_whole_board(self):
        record = self.play({
            "s001-exact-edit": [{"write": {"notes/meeting.md": CORRECT}}],
            "s002-json-repair": [{"write": {"config/app.json": MANIFEST}}],
        }, board="two.yaml")
        self.assertEqual(len(record.stages), 2)
        self.assertEqual(record.stage_reached, 2)


class ConfigTest(HarnessCase):
    def test_only_selects_one_stage(self):
        record = self.play({}, board="two.yaml", only="s001-exact-edit")
        self.assertEqual(len(record.stages), 1)

    def test_limit_caps_the_board(self):
        record = self.play({}, board="two.yaml", limit=1)
        self.assertEqual(len(record.stages), 1)

    def test_unknown_stage_filter_is_an_error(self):
        with self.assertRaises(SpecError):
            self.play({}, board="two.yaml", only="s999-nope")


class EventStreamTest(HarnessCase):
    def test_attempt_events_carry_the_verdict(self):
        self.play({"s001-exact-edit": [{"write": {"notes/meeting.md": CORRECT}}]})
        ended = [e for e in self.events if e["event"] == "attempt.ended"]
        self.assertEqual(ended[0]["verdict"], VERDICT_PASS)

    def test_failed_attempt_lists_what_failed(self):
        self.play({})
        ended = [e for e in self.events if e["event"] == "attempt.ended"]
        self.assertEqual(ended[0]["verdict"], VERDICT_FAIL)
        self.assertTrue(ended[0]["failed"])


class RelativeOutDirTest(unittest.TestCase):
    """`--out runs` is what the README tells people to type.

    Oracles run with their cwd inside the sandbox, so a relative out directory
    used to resolve the checker path against the workspace and every script
    oracle reported "checker produced no verdict" — an agent failure caused by
    the harness, which is the one thing an instrument must never do.
    """

    def test_script_oracles_are_found_from_a_relative_out_dir(self):
        tmp = Path(tempfile.mkdtemp(prefix="orch-rel-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        cwd = os.getcwd()
        os.chdir(tmp)
        self.addCleanup(os.chdir, cwd)

        config = RunConfig(board=load_board(BOARDS / "v1.yaml"), harness="fake",
                           out_dir="relative-runs", run_id="rel",
                           only="s003-rename-symbol")
        record = Orchestrator(config, FakeHarness({}, model="fake", default="noop")).run()

        checks = [c.name for c in record.stages[0].attempts[0].checks]
        self.assertIn("old-name-gone", checks, "the checker never ran")
        self.assertNotIn("checker.py:error", checks)
        self.assertTrue((tmp / "relative-runs" / "rel" / "run.json").exists())


class StageClockTest(unittest.TestCase):
    """DESIGN.md §5: the wall clock budget belongs to the stage, not the attempt."""

    class Probe(FakeHarness):
        def __init__(self):
            super().__init__({}, model="probe", default="noop")
            self.timeouts: list[int] = []

        def run(self, request):
            self.timeouts.append(request.timeout_s)
            time.sleep(1.2)
            return super().run(request)

    def test_later_attempts_get_what_is_left_of_the_clock(self):
        tmp = Path(tempfile.mkdtemp(prefix="orch-clock-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        board = load_board(BOARDS / "smoke.yaml")
        board.stages[0].timeout_s = 8
        probe = self.Probe()
        config = RunConfig(board=board, harness="fake", out_dir=tmp, run_id="clock")
        record = Orchestrator(config, probe).run()

        self.assertEqual(len(probe.timeouts), 3)
        self.assertEqual(probe.timeouts, sorted(probe.timeouts, reverse=True))
        self.assertLess(probe.timeouts[1], probe.timeouts[0])
        self.assertLess(probe.timeouts[2], probe.timeouts[1])
        self.assertGreaterEqual(probe.timeouts[0], 6, "attempt 1 should get the stage budget")
        self.assertEqual(record.stages[0].attempts_used, 3)

    def test_a_stage_with_no_clock_left_is_not_given_a_fresh_budget(self):
        tmp = Path(tempfile.mkdtemp(prefix="orch-clock-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        board = load_board(BOARDS / "smoke.yaml")
        board.stages[0].timeout_s = 1
        probe = self.Probe()
        config = RunConfig(board=board, harness="fake", out_dir=tmp, run_id="clock2")
        record = Orchestrator(config, probe).run()

        self.assertEqual(probe.timeouts, [], "a stage out of clock must not run")
        self.assertEqual([a.verdict for a in record.stages[0].attempts],
                         [VERDICT_BUDGET])


class ReferenceRunTest(unittest.TestCase):
    """`--harness solve` installs each stage's own fixed control.

    If the reference cannot walk the whole board through the real game loop,
    then a stage is broken and no agent result on it means anything.
    """

    def test_the_reference_clears_every_stage_on_the_board(self):
        tmp = Path(tempfile.mkdtemp(prefix="orch-ref-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        config = RunConfig(board=load_board(BOARDS / "v1.yaml"), harness="solve",
                           out_dir=tmp, run_id="ref")
        record = Orchestrator(config, SolveHarness()).run()

        self.assertEqual(record.stage_reached, 10,
                         f"stopped at {record.stopped_at}")
        self.assertEqual(record.stopped_at, "complete")
        self.assertEqual(record.first_try_rate, 1.0)
        self.assertEqual(record.points, 2340.0)

    def test_a_control_replaces_the_workspace_it_does_not_overlay(self):
        """Passing a stage can mean deleting a file; overlaying would undo that."""
        tmp = Path(tempfile.mkdtemp(prefix="orch-ref-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        stages = tmp / "stages" / "sx" / "controls" / "fixed"
        stages.mkdir(parents=True)
        (stages / "keep.txt").write_text("kept")
        workspace = tmp / "ws"
        workspace.mkdir()
        (workspace / "gone.txt").write_text("must not survive")
        (workspace / "keep.txt").write_text("stale")

        harness = SolveHarness(stages_dir=tmp / "stages")
        request = HarnessRequest(prompt="x", workspace=workspace, timeout_s=5,
                                 stage_id="sx", attempt=1)
        harness.run(request)
        self.assertFalse((workspace / "gone.txt").exists())
        self.assertEqual((workspace / "keep.txt").read_text(), "kept")


if __name__ == "__main__":
    unittest.main()
