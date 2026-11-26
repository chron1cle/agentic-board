"""Calibration must sample levels that ordinary play never reaches."""

import json
import tempfile
import unittest
from pathlib import Path

from engine.calibration import calibrate, difficulty_groups
from engine.harness.fake import FakeHarness
from engine.harness.solve import SolveHarness
from engine.spec import BoardSegment, load_board

ROOT = Path(__file__).resolve().parents[1]


class CalibrationTest(unittest.TestCase):
    def test_correct_workspace_at_timeout_earns_a_first_try_clear(self):
        class StalledSolve(SolveHarness):
            def run(self, request):
                result = super().run(request)
                result.timed_out = True
                return result

        board = load_board(ROOT / "boards" / "smoke.yaml")
        board.segments = [BoardSegment(1, 1)]
        with tempfile.TemporaryDirectory() as tmp:
            path, levels = calibrate(board, 1, "solve", StalledSolve(), None, [1], tmp, report=lambda _: None)
            level = levels[0]
            self.assertEqual((level["clears"], level["budgetExhaustions"]), (1, 1))
            trial = level["trials"][0]
            self.assertEqual(trial["lastVerdict"], "pass")
            self.assertEqual(trial["timeoutArtifact"]["status"], "pass")
            self.assertEqual(trial["timeoutArtifact"]["attempt"], trial["attempts"])
            record = json.loads((path.parent / trial["record"]).read_text())
            self.assertEqual(record["stages"][0]["points"], 120)
            self.assertTrue(record["stages"][0]["attempts"][0]["timed_out"])
            self.assertEqual(record["scoreSegments"][0]["score"], 100)
            self.assertEqual(record["final"]["firstTryRate"], 1.0)

    def test_an_incomplete_trial_is_separate_from_a_completed_rejection(self):
        class SometimesInterrupted(FakeHarness):
            def run(self, request):
                result = super().run(request)
                result.timed_out = request.stage_id == "s001-exact-edit"
                return result

        board = load_board(ROOT / "boards" / "v4.yaml")
        board.segments = [BoardSegment(1, 2)]
        with tempfile.TemporaryDirectory() as tmp:
            path, levels = calibrate(board, 1, "fake", SometimesInterrupted(), None, [1], tmp,
                                     report=lambda _: None)
            data = json.loads(path.read_text())
            trial = levels[0]["trials"][0]
            self.assertEqual((trial["status"], trial["lastVerdict"], trial["attempts"]),
                             ("incomplete", "incomplete", 1))
            self.assertEqual(trial["timeoutArtifact"]["status"], "fail")
            self.assertEqual((data["summary"]["clearRate"], data["summary"]["validTrials"],
                              data["summary"]["incompleteTrials"]), (0, 1, 1))
            self.assertEqual(data["difficultyGroups"][0]["stages"], [levels[1]["stage"]])

    def test_difficulty_uses_matched_trials_and_leaves_ties_together(self):
        levels = [dict(stage=name, validTrials=n, clears=clears, firstTryPasses=first)
                  for name, n, clears, first in [
                      ("retry", 3, 2, 1), ("tie", 3, 2, 1), ("easy", 3, 2, 2),
                      ("incomplete", 2, 2, 2), ("never", 3, 0, 0)]]
        self.assertEqual([group["stages"] for group in difficulty_groups(levels, 3)],
                         [["easy"], ["retry", "tie"], ["never"]])

    def test_level_after_failure_still_runs_on_each_seed(self):
        board = load_board(ROOT / "boards" / "v3.yaml")
        fixed = board.stages[-1].path / "controls" / "fixed"
        harness = FakeHarness({
            board.stages[-1].id: [{"write": {file.name: file.read_text() for file in fixed.glob("*.py")}}],
        })
        with tempfile.TemporaryDirectory() as tmp:
            path, levels = calibrate(board, 3, "fake", harness, None, [1, 37], tmp, report=lambda _: None)
            data = json.loads(path.read_text())
            self.assertEqual(data["seeds"], [1, 37])
            self.assertEqual(len(levels), 10)
            self.assertEqual(levels[0]["clears"], 0)
            self.assertEqual(levels[-1]["firstTryPasses"], 2)
            self.assertEqual(levels[-1]["validTrials"], 2)
            self.assertTrue((path.parent / levels[-1]["trials"][0]["record"]).is_file())
            self.assertEqual(data["difficultyGroups"][0]["stages"], [board.stages[-1].id])
            self.assertEqual(levels[-1]["trials"][0]["lastVerdict"], "pass")
            self.assertEqual(data["summary"], {"clears": 2, "validTrials": 20,
                                              "plannedTrials": 20, "incompleteTrials": 0,
                                              "invalidTrials": 0, "clearRate": 0.1})
