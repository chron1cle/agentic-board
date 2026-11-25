"""Scoring formulas and the two headline metrics."""

import unittest

from engine.feedback import AttemptRecord, VERDICT_FAIL, VERDICT_PASS
from engine.scoring import (budget_penalty, feedback_uptake, first_try_rate, score_stage,
                            stage_value)


class Stage:
    def __init__(self, tier):
        self.tier = tier


class ValueTest(unittest.TestCase):
    def test_ladder(self):
        self.assertEqual([stage_value(t) for t in range(1, 7)],
                         [100, 150, 200, 250, 300, 350])

    def test_base_scales(self):
        self.assertEqual(stage_value(2, base=200), 300)


class ScoreStageTest(unittest.TestCase):
    def test_first_try_gets_the_bonus(self):
        self.assertEqual(score_stage(1, 1), 120.0)

    def test_later_attempts_are_worth_less(self):
        self.assertEqual(score_stage(1, 2), 75.0)
        self.assertEqual(score_stage(1, 3), 50.0)

    def test_higher_tier_is_worth_more(self):
        self.assertGreater(score_stage(6, 1), score_stage(1, 1))

    def test_over_budget_is_penalised(self):
        self.assertEqual(score_stage(1, 1, tools_used=40, tool_budget=40), 120.0)
        self.assertEqual(score_stage(1, 1, tools_used=50, tool_budget=40), 114.0)

    def test_beating_the_reference_earns_the_speed_bonus(self):
        self.assertEqual(score_stage(1, 1, seconds=5, reference_seconds=10), 126.0)

    def test_unknown_attempt_number_is_treated_as_last(self):
        self.assertEqual(score_stage(1, 9), 50.0)


class BudgetPenaltyTest(unittest.TestCase):
    def test_under_budget_is_never_punished(self):
        self.assertEqual(budget_penalty(1, 100), 0.0)
        self.assertEqual(budget_penalty(100, 100), 0.0)

    def test_scales_in_quarter_steps(self):
        self.assertEqual(budget_penalty(124, 100), 0.0)
        self.assertEqual(budget_penalty(125, 100), 0.05)
        self.assertEqual(budget_penalty(200, 100), 0.20)

    def test_zero_budget_is_safe(self):
        self.assertEqual(budget_penalty(10, 0), 0.0)


class Result:
    """Duck-typed StageResult for the metric functions."""

    def __init__(self, cleared, attempts_used, attempts=()):
        self.cleared = cleared
        self.attempts_used = attempts_used
        self.attempts = list(attempts)


class MetricTest(unittest.TestCase):
    def test_first_try_rate_ignores_uncleared_stages(self):
        results = [Result(True, 1), Result(True, 2), Result(False, 3)]
        self.assertAlmostEqual(first_try_rate(results), 0.5)

    def test_first_try_rate_with_nothing_cleared(self):
        self.assertEqual(first_try_rate([Result(False, 3)]), 0.0)

    def test_feedback_uptake_counts_fail_then_pass(self):
        results = [Result(True, 2, [AttemptRecord(1, VERDICT_FAIL),
                                    AttemptRecord(2, VERDICT_PASS)])]
        self.assertAlmostEqual(feedback_uptake(results), 1.0)

    def test_feedback_uptake_counts_fail_then_fail(self):
        results = [Result(False, 3, [AttemptRecord(1, VERDICT_FAIL),
                                     AttemptRecord(2, VERDICT_FAIL),
                                     AttemptRecord(3, VERDICT_FAIL)])]
        self.assertEqual(feedback_uptake(results), 0.0)

    def test_feedback_uptake_pools_transitions_across_stages(self):
        results = [
            Result(True, 2, [AttemptRecord(1, VERDICT_FAIL), AttemptRecord(2, VERDICT_PASS)]),
            Result(True, 3, [AttemptRecord(1, VERDICT_FAIL), AttemptRecord(2, VERDICT_FAIL),
                             AttemptRecord(3, VERDICT_PASS)]),
        ]
        # three failed attempts were followed by another try; two of those turned
        # into a pass, one did not
        self.assertAlmostEqual(feedback_uptake(results), round(2 / 3, 4))

    def test_feedback_uptake_with_no_transitions(self):
        self.assertEqual(feedback_uptake([Result(True, 1, [AttemptRecord(1, VERDICT_PASS)])]), 0.0)


class SegmentScoringTest(unittest.TestCase):
    def test_same_attempt_fraction_in_both_halves(self):
        from pathlib import Path

        from engine.scoring import segment_scores
        from engine.spec import load_board

        board = load_board(Path(__file__).resolve().parents[1] / "boards" / "v2.yaml")
        ids = [stage.id for stage in board.stages]
        rows = [
            {"stage": stage.id, "cleared": True,
             "points": score_stage(stage.tier, 1, base=stage.score_base)}
            for stage in [*board.stages[:5], *board.stages[10:15]]
        ]
        self.assertEqual([score["score"] for score in segment_scores(board, ids, rows)], [50, 50])
        self.assertEqual([score["range"] for score in segment_scores(board, ids[10:], rows)], ["11-20"])


if __name__ == "__main__":
    unittest.main()
