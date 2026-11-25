"""The CLI surface: what a person typing commands actually gets."""

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from engine.cli import build_parser, main, write_index
from engine.runrecord import RunRecord, StageResult

ROOT = Path(__file__).resolve().parent.parent


def run_cli(*argv) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(argv))
    return code, buffer.getvalue()


class ValidateTest(unittest.TestCase):
    def test_the_shipped_board_validates(self):
        code, out = run_cli("validate")
        self.assertEqual(code, 0)
        self.assertIn("10 stages", out)
        self.assertIn("s010-codemod-migration", out)

    def test_a_broken_board_is_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            path.write_text("id: bad\nstages:\n  - nope\n")
            code, _ = run_cli("validate", "--board", str(path))
            self.assertEqual(code, 1)


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cli-"))
        record = RunRecord(run="r1", harness="fake", model="m", board="b",
                           board_version="1", seed=1)
        record.stages = [StageResult(id="s1", name="S1", tier=1, cleared=True,
                                     attempts_used=1, points=120.0, seconds=3.0)]
        record.save(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_report_by_directory(self):
        code, out = run_cli("report", str(self.tmp))
        self.assertEqual(code, 0)
        self.assertIn("stageReached", out)
        self.assertIn("s1", out)

    def test_report_by_file(self):
        code, out = run_cli("report", str(self.tmp / "run.json"))
        self.assertEqual(code, 0)
        self.assertIn("stageReached", out)

    def test_missing_run_is_exit_1(self):
        code, _ = run_cli("report", str(self.tmp / "nowhere"))
        self.assertEqual(code, 1)


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cli-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, run_id, harness, model, reached, points):
        record = RunRecord(run=run_id, harness=harness, model=model, board="b",
                           board_version="1", seed=1)
        for n in range(1, 4):
            record.stages.append(StageResult(
                id=f"s{n}", name=f"S{n}", tier=n, cleared=n <= reached,
                attempts_used=1, points=points if n <= reached else 0.0))
        record.save(self.tmp / run_id)

    def test_index_lists_every_run_best_first(self):
        self._write("r-bad", "fake", "weak", 1, 100.0)
        self._write("r-good", "fake", "strong", 3, 100.0)
        data = json.loads(write_index(self.tmp).read_text())
        self.assertEqual([e["model"] for e in data["runs"]], ["strong", "weak"])
        self.assertEqual(data["runs"][0]["stageReached"], 3)

    def test_index_carries_the_timeline_for_replay(self):
        self._write("r1", "fake", "m", 2, 50.0)
        entry = json.loads(write_index(self.tmp).read_text())["runs"][0]
        self.assertEqual(len(entry["timeline"]), 3)
        self.assertEqual(entry["timeline"][1]["cumulative"], 100.0)

    def test_a_corrupt_run_is_skipped_not_fatal(self):
        self._write("r-good", "fake", "m", 1, 10.0)
        (self.tmp / "r-broken").mkdir()
        (self.tmp / "r-broken" / "run.json").write_text("{not json")
        data = json.loads(write_index(self.tmp).read_text())
        self.assertEqual([e["run"] for e in data["runs"]], ["r-good"])

    def test_index_command_reports_the_count(self):
        self._write("r1", "fake", "m", 1, 10.0)
        code, out = run_cli("index", "--out", str(self.tmp))
        self.assertEqual(code, 0)
        self.assertIn("1 run(s) indexed", out)


class RunCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cli-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_with_the_fake_harness_writes_everything(self):
        code, out = run_cli("run", "--board", str(ROOT / "boards" / "smoke.yaml"),
                            "--harness", "fake", "--out", str(self.tmp),
                            "--run-id", "cli-run")
        self.assertIn("run ended", out)
        self.assertTrue((self.tmp / "cli-run" / "run.json").exists())
        self.assertTrue((self.tmp / "cli-run" / "events.jsonl").exists())
        self.assertTrue((self.tmp / "index.json").exists())

    def test_an_uncleared_board_exits_nonzero(self):
        code, _ = run_cli("run", "--board", str(ROOT / "boards" / "smoke.yaml"),
                          "--harness", "fake", "--out", str(self.tmp),
                          "--run-id", "cli-run2", "--quiet")
        self.assertEqual(code, 1)

    def test_an_unknown_harness_is_refused_by_the_parser(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["run", "--harness", "no-such-harness"])

    def test_limit_is_passed_through(self):
        code, out = run_cli("run", "--board", str(ROOT / "boards" / "two.yaml"),
                            "--harness", "fake", "--out", str(self.tmp),
                            "--run-id", "cli-run3", "--limit", "1", "--quiet")
        data = json.loads((self.tmp / "cli-run3" / "run.json").read_text())
        self.assertEqual(len(data["stages"]), 1)


class ParserTest(unittest.TestCase):
    def test_a_command_is_required(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args([])

    def test_harness_choices_come_from_the_registry(self):
        args = build_parser().parse_args(["run", "--harness", "fake"])
        self.assertEqual(args.harness, "fake")


if __name__ == "__main__":
    unittest.main()
