"""The run record is the score sheet and the replay tape in one file."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.feedback import AttemptRecord, VERDICT_FAIL, VERDICT_PASS
from engine.oracles import Check
from engine.runrecord import RunRecord, StageResult, SCHEMA_VERSION


def stage(sid, tier, cleared, attempts_used, points, attempts=(), **kw):
    return StageResult(id=sid, name=sid.title(), tier=tier, region="r",
                       cleared=cleared, attempts_used=attempts_used, points=points,
                       attempts=list(attempts), tool_calls=kw.get("tool_calls", 3),
                       seconds=kw.get("seconds", 10.0), tokens=kw.get("tokens", 500))


class DerivedMetricsTest(unittest.TestCase):
    def setUp(self):
        self.record = RunRecord(run="r1", harness="fake", model="m", board="b",
                                board_version="1", seed=7)
        self.record.stages = [
            stage("s1", 1, True, 1, 120.0, [AttemptRecord(1, VERDICT_PASS)]),
            stage("s2", 2, True, 2, 112.5, [AttemptRecord(1, VERDICT_FAIL),
                                           AttemptRecord(2, VERDICT_PASS)]),
            stage("s3", 3, False, 3, 0.0, [AttemptRecord(n, VERDICT_FAIL) for n in (1, 2, 3)]),
        ]

    def test_points_are_the_sum(self):
        self.assertEqual(self.record.points, 232.5)

    def test_stage_reached_counts_clears(self):
        self.assertEqual(self.record.stage_reached, 2)

    def test_stopped_at_names_the_locked_door(self):
        self.assertEqual(self.record.stopped_at, "s3")

    def test_stopped_at_is_complete_when_all_cleared(self):
        self.record.stages[2].cleared = True
        self.assertEqual(self.record.stopped_at, "complete")

    def test_first_try_rate(self):
        self.assertAlmostEqual(self.record.first_try_rate, 0.5)

    def test_feedback_uptake(self):
        # failed attempts followed by another try: s2 attempt1, s3 attempts 1 and 2
        self.assertAlmostEqual(self.record.feedback_uptake, round(1 / 3, 4))

    def test_totals(self):
        self.assertEqual(self.record.totals["tool_calls"], 9)
        self.assertEqual(self.record.totals["tokens"], 1500)
        self.assertEqual(self.record.totals["attempts"], 6)


class TimelineTest(unittest.TestCase):
    def test_timeline_is_cumulative_and_ordered(self):
        record = RunRecord(run="r", harness="f", model="m", board="b",
                           board_version="1", seed=1)
        record.stages = [stage("s1", 1, True, 1, 100.0), stage("s2", 2, True, 1, 150.0)]
        timeline = record.cumulative_score()
        self.assertEqual([row["index"] for row in timeline], [1, 2])
        self.assertEqual([row["cumulative"] for row in timeline], [100.0, 250.0])
        self.assertEqual(timeline[-1]["points"], 150.0)

    def test_timeline_carries_what_the_renderer_needs(self):
        record = RunRecord(run="r", harness="f", model="m", board="b",
                           board_version="1", seed=1)
        record.stages = [stage("s1", 1, True, 2, 75.0)]
        row = record.cumulative_score()[0]
        for key in ("stage", "name", "tier", "region", "cleared", "attempts",
                    "cumulative", "seconds", "tool_calls"):
            self.assertIn(key, row)


class SerializationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rr-"))
        self.record = RunRecord(run="r1", harness="fake", model="m", board="b",
                                board_version="1", seed=3)
        self.record.stages = [stage("s1", 1, True, 1, 120.0, [AttemptRecord(1, VERDICT_PASS)])]
        self.record.finished = 1000.0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_saved_file_is_json_and_round_trips(self):
        path = self.record.save(self.tmp / "run")
        loaded = RunRecord.load(path)
        self.assertEqual(loaded["run"], "r1")
        self.assertEqual(loaded["schema"], SCHEMA_VERSION)
        self.assertEqual(loaded["final"]["stageReached"], 1)
        self.assertEqual(len(loaded["timeline"]), 1)

    def test_final_block_is_the_headline_summary(self):
        final = self.record.as_dict()["final"]
        self.assertEqual(
            sorted(final),
            sorted(["stageReached", "stoppedAt", "points", "firstTryRate",
                    "feedbackUptake", "boardSize", "tool_calls", "seconds",
                    "tokens", "attempts"]))

    def test_attempts_survive_serialization(self):
        record = RunRecord(run="r", harness="f", model="m", board="b",
                           board_version="1", seed=1)
        record.stages = [stage("s1", 1, False, 2, 0.0,
                               [AttemptRecord(1, VERDICT_FAIL, [Check("c", False, "nope")])])]
        data = json.loads(record.save(self.tmp / "run2").read_text())
        attempt = data["stages"][0]["attempts"][0]
        self.assertEqual(attempt["verdict"], "fail")
        self.assertEqual(attempt["checks"][0]["detail"], "nope")

    def test_save_creates_missing_directories(self):
        self.assertTrue((self.record.save(self.tmp / "deep" / "deeper") ).exists())


if __name__ == "__main__":
    unittest.main()
