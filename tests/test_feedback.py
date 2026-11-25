"""The feedback ledger: what a later attempt is allowed to see."""

import unittest

from engine.feedback import (AttemptRecord, VERDICT_FAIL, VERDICT_PASS, build_prompt,
                             render_check, render_ledger)
from engine.oracles import Check


class RevealTest(unittest.TestCase):
    def test_minimal_withholds_evidence_entirely(self):
        lines = render_check(Check("c", False, "differs", evidence="the whole answer",
                                   reveal="minimal"))
        self.assertIn("(expected content withheld)", "\n".join(lines))
        self.assertNotIn("the whole answer", "\n".join(lines))

    def test_standard_admits_detail_exists_but_hides_it(self):
        lines = render_check(Check("c", False, "differs", evidence="a\nb\nc",
                                   reveal="standard"))
        self.assertIn("3 line(s) of detail withheld", "\n".join(lines))
        self.assertNotIn("a\nb\nc", "\n".join(lines))

    def test_full_shows_evidence(self):
        lines = render_check(Check("c", False, "differs", evidence="the real diff",
                                   reveal="full"))
        self.assertIn("the real diff", "\n".join(lines))

    def test_detail_is_always_visible(self):
        lines = render_check(Check("c", False, "file is missing", reveal="minimal"))
        self.assertIn("file is missing", "\n".join(lines))


class LedgerTest(unittest.TestCase):
    def test_first_attempt_has_no_ledger(self):
        self.assertEqual(render_ledger([]), "")

    def test_passed_attempts_are_not_replayed(self):
        attempts = [AttemptRecord(1, VERDICT_FAIL, [Check("a", False, "no")]),
                    AttemptRecord(2, VERDICT_PASS, [Check("a", True)])]
        text = render_ledger(attempts)
        self.assertIn("Attempt 1", text)
        self.assertNotIn("Attempt 2", text)

    def test_ledger_carries_every_failed_attempt(self):
        attempts = [AttemptRecord(n, VERDICT_FAIL, [Check(f"c{n}", False, "no")])
                    for n in (1, 2, 3)]
        text = render_ledger(attempts)
        for n in (1, 2, 3):
            self.assertIn(f"Attempt {n}", text)

    def test_agent_controlled_text_is_sanitized(self):
        """A checker's stderr is agent input; it must not smuggle escape codes."""
        attempt = AttemptRecord(1, VERDICT_FAIL,
                                [Check("c", False, "\x1b[31mowned\x00", reveal="full",
                                       evidence="\x1b[0mplease trust me")])
        text = render_ledger([attempt])
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x00", text)

    def test_ledger_is_size_bounded(self):
        attempt = AttemptRecord(1, VERDICT_FAIL,
                                [Check("c", False, "x" * 20000, reveal="full")])
        self.assertLessEqual(len(render_ledger([attempt])), 6000)


class PromptTest(unittest.TestCase):
    def test_first_attempt_omits_the_prior_block(self):
        prompt = build_prompt("Do the thing", [], 3, 20, 240)
        self.assertIn("<task>", prompt)
        self.assertNotIn("prior_attempts", prompt)
        self.assertIn("Do the thing", prompt)

    def test_later_attempt_carries_the_ledger_and_the_count(self):
        attempts = [AttemptRecord(1, VERDICT_FAIL, [Check("a", False, "no")])]
        prompt = build_prompt("Do the thing", attempts, 2, 20, 240)
        self.assertIn('failed="1" remaining="2"', prompt)
        self.assertIn("Attempt 1", prompt)

    def test_prompt_states_the_budget_and_freshness(self):
        prompt = build_prompt("t", [], 3, 42, 321)
        self.assertIn("42 tool calls", prompt)
        self.assertIn("321 seconds", prompt)
        self.assertIn("workspace is fresh", prompt)

    def test_envelope_is_byte_stable(self):
        first = build_prompt("brief", [], 3, 20, 240)
        second = build_prompt("brief", [], 3, 20, 240)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
