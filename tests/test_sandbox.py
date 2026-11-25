"""Workspace provisioning, diffing, integrity, and the pinned environment."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.sandbox import Sandbox, normalize_text, snapshot_hashes
from engine.spec import load_stage

ROOT = Path(__file__).resolve().parent.parent
STAGES = ROOT / "stages"


class NormalizeTest(unittest.TestCase):
    def test_no_ops_returns_input(self):
        self.assertEqual(normalize_text("a\nb", []), "a\nb")

    def test_strip_trailing_ws(self):
        self.assertEqual(normalize_text("a  \nb\t", ["strip-trailing-ws"]), "a\nb")

    def test_collapse_blank(self):
        self.assertEqual(normalize_text("a\n\n\n\nb", ["collapse-blank"]), "a\n\nb")

    def test_collapse_blank_drops_leading_runs(self):
        self.assertEqual(normalize_text("\n\n\na", ["collapse-blank"]), "a")

    def test_sort_lines(self):
        self.assertEqual(normalize_text("b\na", ["sort-lines"]), "a\nb")

    def test_trim_edges(self):
        self.assertEqual(normalize_text("\n\na\n\n", ["trim-edges"]), "a")

    def test_ops_compose_in_declared_order(self):
        self.assertEqual(normalize_text("  a  \n\n  b  \n",
                                        ["strip-trailing-ws", "trim-edges"]), "  a\n\n  b")


class ProvisionTest(unittest.TestCase):
    def setUp(self):
        self.stage = load_stage(STAGES / "s001-exact-edit" / "stage.yaml")
        self.tmp = Path(tempfile.mkdtemp(prefix="sbx-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_two_provisions_are_identical(self):
        first = Sandbox.provision(self.stage, self.tmp / "a")
        second = Sandbox.provision(self.stage, self.tmp / "b")
        self.assertEqual(first.fingerprint(), second.fingerprint())

    def test_provision_is_dirty_after_edit_then_clean_again(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        target = box.workspace / "notes" / "meeting.md"
        target.write_text("wrecked")
        self.assertNotEqual(box.delta().changed_lines, 0)
        again = Sandbox.provision(self.stage, self.tmp / "a")
        self.assertEqual(again.delta().changed_lines, 0)

    def test_delta_reports_added_and_removed(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        (box.workspace / "new.txt").write_text("hi")
        (box.workspace / "notes" / "meeting.md").unlink()
        delta = box.delta()
        self.assertIn("new.txt", delta.added)
        self.assertIn("notes/meeting.md", delta.removed)

    def test_unified_diff_shows_the_change(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        target = box.workspace / "notes" / "meeting.md"
        target.write_text(target.read_text().replace("recieve", "receive"))
        self.assertIn("+We will receive", box.unified_diff())

    def test_binary_files_do_not_crash_diffing(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        (box.workspace / "blob.bin").write_bytes(b"\x00\x01\x02\xff")
        self.assertIn("blob.bin", box.delta().added)

    def test_run_uses_pinned_environment(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        result = box.run("echo $LC_ALL-$TZ")
        self.assertEqual(result.stdout.strip(), "C-UTC")
        self.assertTrue(result.ok)

    def test_run_captures_exit_code_and_timeout(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        self.assertEqual(box.run("exit 7").exit_code, 7)
        slow = box.run("sleep 5", timeout=1)
        self.assertTrue(slow.timed_out)
        self.assertFalse(slow.ok)

    def test_secret_environment_is_not_inherited(self):
        os.environ["BOARD_TEST_API_KEY"] = "should-not-leak"
        try:
            box = Sandbox.provision(self.stage, self.tmp / "a")
            found = box.run('sh -c \'if [ -n "$BOARD_TEST_API_KEY" ]; then echo leak; fi\'')
            self.assertEqual(found.stdout.strip(), "")
        finally:
            del os.environ["BOARD_TEST_API_KEY"]

    def test_integrity_violation_when_protected_file_changes(self):
        stage = load_stage(STAGES / "s005-log-search" / "stage.yaml")
        box = Sandbox.provision(stage, self.tmp / "a")
        self.assertEqual(box.integrity_violations(), [])
        (box.workspace / "logs" / "app.log").write_text("tampered")
        self.assertEqual(box.integrity_violations(), ["logs/app.log"])

    def test_deleting_a_protected_file_is_a_violation(self):
        stage = load_stage(STAGES / "s005-log-search" / "stage.yaml")
        box = Sandbox.provision(stage, self.tmp / "a")
        (box.workspace / "logs" / "app.log").unlink()
        self.assertEqual(box.integrity_violations(), ["logs/app.log"])

    def test_snapshot_hashes_marks_missing(self):
        box = Sandbox.provision(self.stage, self.tmp / "a")
        self.assertEqual(snapshot_hashes(box.workspace, ["nope.txt"])["nope.txt"], "<missing>")


if __name__ == "__main__":
    unittest.main()
