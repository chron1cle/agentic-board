"""Every oracle kind, including what it reveals and what it hides."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.oracles import (Command, DiffBudget, FileExact, FileNormalized, JsonEqual,
                            Mutation, Script, Timing, parse_script_output, sanitize)
from engine.sandbox import Sandbox, CommandResult


def make_box(files, oracle_files=None, protected=None):
    """A sandbox with `files` in the workspace and `oracle_files` outside it."""
    tmp = Path(tempfile.mkdtemp(prefix="ora-"))
    (tmp / "workspace").mkdir()
    for rel, text in files.items():
        target = tmp / "workspace" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    shutil.copytree(tmp / "workspace", tmp / "_original")
    oracle = tmp / "hidden_oracle"
    oracle.mkdir()
    for rel, text in (oracle_files or {}).items():
        target = oracle / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    box = Sandbox(tmp, tmp / "_original", protected or [])
    box.oracle_dir = oracle
    return box


class CleanupMixin:
    def tearDown(self):
        if hasattr(self, "box"):
            shutil.rmtree(self.box.root, ignore_errors=True)


class SanitizeTest(unittest.TestCase):
    def test_strips_control_characters(self):
        self.assertEqual(sanitize("ok\x1b[31mred\x00"), "ok[31mred")

    def test_truncates(self):
        self.assertEqual(len(sanitize("x" * 5000, 100)), 100)

    def test_none_is_empty(self):
        self.assertEqual(sanitize(None), "")


class FileExactTest(CleanupMixin, unittest.TestCase):
    def test_match(self):
        self.box = make_box({"out.txt": "hello"}, {"key.txt": "hello"})
        check = FileExact({"path": "out.txt", "expect": "key.txt"}).run(self.box)[0]
        self.assertTrue(check.ok)
        self.assertEqual(check.tier, "A")

    def test_mismatch_hides_the_expected_bytes(self):
        self.box = make_box({"out.txt": "hallo"}, {"key.txt": "hello"})
        check = FileExact({"path": "out.txt", "expect": "key.txt"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertNotIn("hello", check.detail)
        self.assertNotIn("hello", check.evidence)
        self.assertIn("byte 1", check.evidence)

    def test_missing_file(self):
        self.box = make_box({}, {"key.txt": "hello"})
        check = FileExact({"path": "out.txt", "expect": "key.txt"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("missing", check.detail)


class FileNormalizedTest(CleanupMixin, unittest.TestCase):
    def test_whitespace_only_difference_passes(self):
        self.box = make_box({"a.md": "one  \ntwo"}, {"k.md": "one\ntwo"})
        check = FileNormalized({"path": "a.md", "expect": "k.md",
                                "normalize": ["strip-trailing-ws"]}).run(self.box)[0]
        self.assertTrue(check.ok)

    def test_reports_offending_line_numbers(self):
        self.box = make_box({"a.md": "one\ntwo\nthree"}, {"k.md": "one\nTWO\nthree"})
        check = FileNormalized({"path": "a.md", "expect": "k.md"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("line 2", check.detail)

    def test_length_mismatch_is_reported(self):
        self.box = make_box({"a.md": "one\ntwo"}, {"k.md": "one"})
        check = FileNormalized({"path": "a.md", "expect": "k.md"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("differ", check.detail)


class JsonEqualTest(CleanupMixin, unittest.TestCase):
    def test_key_order_ignored(self):
        self.box = make_box({"a.json": '{"b": 2, "a": 1}'}, {"k.json": '{"a": 1, "b": 2}'})
        self.assertTrue(JsonEqual({"path": "a.json", "expect": "k.json"}).run(self.box)[0].ok)

    def test_names_the_differing_field_not_its_value(self):
        self.box = make_box({"a.json": '{"n": 3}'}, {"k.json": '{"n": 4}'})
        check = JsonEqual({"path": "a.json", "expect": "k.json"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("$.n", check.detail)
        self.assertNotIn("4", check.detail)

    def test_missing_and_unexpected_keys(self):
        self.box = make_box({"a.json": '{"x": 1}'}, {"k.json": '{"y": 1}'})
        check = JsonEqual({"path": "a.json", "expect": "k.json"}).run(self.box)[0]
        self.assertIn("(missing)", check.detail)
        self.assertIn("(unexpected)", check.detail)

    def test_invalid_json_is_reported_not_raised(self):
        self.box = make_box({"a.json": "{nope"}, {"k.json": "{}"})
        check = JsonEqual({"path": "a.json", "expect": "k.json"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("not valid JSON", check.detail)

    def test_list_length_mismatch(self):
        self.box = make_box({"a.json": "[1,2]"}, {"k.json": "[1,2,3]"})
        check = JsonEqual({"path": "a.json", "expect": "k.json"}).run(self.box)[0]
        self.assertIn("length", check.detail)


class DiffBudgetTest(CleanupMixin, unittest.TestCase):
    def test_under_budget(self):
        self.box = make_box({"a.txt": "one\n"})
        (self.box.workspace / "a.txt").write_text("two\n")
        self.assertTrue(DiffBudget({"max_changed_lines": 4}).run(self.box)[0].ok)

    def test_over_budget(self):
        self.box = make_box({"a.txt": "1\n2\n3\n4\n"})
        (self.box.workspace / "a.txt").write_text("a\nb\nc\nd\n")
        check = DiffBudget({"max_changed_lines": 2}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("8 lines changed", check.detail)


class CommandTest(CleanupMixin, unittest.TestCase):
    def test_success(self):
        self.box = make_box({"a.txt": "x"})
        self.assertTrue(Command({"cmd": "test -f a.txt", "name": "exists"}).run(self.box)[0].ok)

    def test_expected_failure(self):
        self.box = make_box({})
        check = Command({"cmd": "exit 3", "name": "boom"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("exit 3", check.detail)

    def test_stdout_comparison(self):
        self.box = make_box({})
        check = Command({"cmd": "echo hi", "expect_stdout": "hi"}).run(self.box)[0]
        self.assertTrue(check.ok)
        check = Command({"cmd": "echo hi", "expect_stdout": "nope"}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("got:", check.evidence)

    def test_timeout_is_a_failure_not_a_crash(self):
        self.box = make_box({})
        check = Command({"cmd": "sleep 3", "timeout_s": 1}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("timed out", check.detail)


class TimingTest(CleanupMixin, unittest.TestCase):
    def test_fast_enough(self):
        self.box = make_box({})
        self.assertTrue(Timing({"cmd": "true", "max_seconds": 5}).run(self.box)[0].ok)

    def test_too_slow(self):
        self.box = make_box({})
        check = Timing({"cmd": "sleep 3", "max_seconds": 1}).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("exceeded", check.detail)


class ScriptParsingTest(unittest.TestCase):
    def test_parses_json_lines_and_ignores_noise(self):
        result = CommandResult("x", 0, 'noise\n{"check":"a","pass":true}\n', "", 1.0)
        checks = parse_script_output(result, "full", "checker.py")
        self.assertEqual([c.name for c in checks], ["a"])
        self.assertTrue(checks[0].ok)

    def test_no_verdict_is_a_failure(self):
        result = CommandResult("x", 1, "", "Traceback...", 1.0)
        checks = parse_script_output(result, "full", "checker.py")
        self.assertFalse(checks[0].ok)
        self.assertIn("Traceback", checks[0].evidence)

    def test_agent_cannot_forge_a_pass_with_plain_stdout(self):
        """A program that prints 'pass' as text must not be read as a verdict."""
        result = CommandResult("x", 0, "pass\ntrue\nok\n", "", 1.0)
        checks = parse_script_output(result, "full", "checker.py")
        self.assertFalse(checks[0].ok)

    def test_a_checker_that_crashes_after_printing_a_pass_cannot_clear(self):
        result = CommandResult("x", 1, '{"check":"a","pass":true}', "", 1.0)
        checks = parse_script_output(result, "full", "checker.py")
        self.assertFalse(checks[-1].ok)
        self.assertEqual(checks[-1].name, "checker.py:error")

    def test_a_string_is_not_a_boolean_verdict(self):
        result = CommandResult("x", 0, '{"check":"a","pass":"false"}', "", 1.0)
        self.assertFalse(parse_script_output(result, "full", "checker.py")[0].ok)

    def test_timeout_is_reported(self):
        result = CommandResult("x", 124, "", "", 1.0, timed_out=True)
        checks = parse_script_output(result, "full", "checker.py")
        self.assertIn("timeout", checks[-1].name)


class ScriptOracleTest(CleanupMixin, unittest.TestCase):
    def test_checker_verdicts_reach_the_result(self):
        script = ('import json\n'
                  'print(json.dumps({"check":"one","pass":True}))\n'
                  'print(json.dumps({"check":"two","pass":False,"detail":"nope"}))\n')
        self.box = make_box({"a.txt": "x"}, {"checker.py": script})
        checks = Script({"entry": "checker.py"}).run(self.box)
        self.assertEqual([c.name for c in checks], ["one", "two"])
        self.assertFalse(all(c.ok for c in checks))

    def test_checker_sees_the_agent_workspace(self):
        script = ('import json,os\n'
                  'print(json.dumps({"check":"saw","pass":os.path.exists("a.txt")}))\n')
        self.box = make_box({"a.txt": "x"}, {"checker.py": script})
        self.assertTrue(Script({"entry": "checker.py"}).run(self.box)[0].ok)


class MutationTest(CleanupMixin, unittest.TestCase):
    CONFIG = {
        "target": "mod.py",
        "test_command": "python3 -c 'import mod,sys; sys.exit(0 if mod.f(3)==6 else 1)'",
        "min_kill_rate": 0.6,
        "mutants": [
            {"name": "m1", "find": "return x * 2", "replace": "return x * 3"},
            {"name": "m2", "find": "return x * 2", "replace": "return x + 2"},
        ],
    }

    def test_good_tests_kill_mutants(self):
        self.box = make_box({"mod.py": "def f(x):\n    return x * 2\n"})
        check = Mutation(dict(self.CONFIG)).run(self.box)[0]
        self.assertTrue(check.ok, check.detail)
        self.assertIn("killed 2/2", check.detail)

    def test_decorative_tests_are_caught(self):
        self.box = make_box({"mod.py": "def f(x):\n    return x * 2\n"})
        config = dict(self.CONFIG)
        config["test_command"] = "python3 -c 'pass'"
        config["min_kill_rate"] = 0.5
        check = Mutation(config).run(self.box)[0]
        self.assertFalse(check.ok)
        self.assertIn("survived", check.detail)

    def test_malformed_mutant_is_a_stage_bug_not_an_agent_failure(self):
        self.box = make_box({"mod.py": "def f(x):\n    return x * 2\n"})
        config = dict(self.CONFIG)
        config["mutants"] = [{"name": "ghost", "find": "not present", "replace": "x"}]
        check = Mutation(config).run(self.box)[0]
        self.assertEqual(check.name, "mutation-setup")
        self.assertFalse(check.ok)
        self.assertIn("not well formed", check.detail)

    def test_mutants_do_not_permanently_modify_the_workspace(self):
        self.box = make_box({"mod.py": "def f(x):\n    return x * 2\n"})
        before = (self.box.workspace / "mod.py").read_text()
        Mutation(dict(self.CONFIG)).run(self.box)
        self.assertEqual((self.box.workspace / "mod.py").read_text(), before)


if __name__ == "__main__":
    unittest.main()
