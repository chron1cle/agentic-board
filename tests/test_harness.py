"""Harness adapters: the fake that drives the tests, and the opencode parser."""

import fcntl
import json
import os
import shutil
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.harness.base import HarnessRequest
from engine.harness.fake import FakeHarness
from engine.harness.opencode import (OpenCodeAdapter, parse_opencode_stream,
                                     resolve_default_model)
from engine.harness import available_harnesses, create

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "opencode_stream.jsonl"


def request_for(workspace, stage_id="s1", attempt=1):
    return HarnessRequest(prompt="do it", workspace=workspace, timeout_s=30,
                          stage_id=stage_id, attempt=attempt)


class FakeHarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fake-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_files_it_is_told_to(self):
        harness = FakeHarness({"s1": [{"write": {"out.txt": "hello"}}]})
        result = harness.run(request_for(self.tmp))
        self.assertEqual((self.tmp / "out.txt").read_text(), "hello")
        self.assertEqual(result.tool_calls, 1)
        self.assertTrue(result.ok)

    def test_actions_run_in_order(self):
        harness = FakeHarness({"s1": [{"write": {"a.txt": "1"}},
                                      {"remove": ["a.txt"]}]})
        harness.run(request_for(self.tmp))
        self.assertFalse((self.tmp / "a.txt").exists())

    def test_unknown_stage_uses_the_default_behaviour(self):
        harness = FakeHarness({"other": [{"write": {"x": "1"}}]}, default="noop")
        result = harness.run(request_for(self.tmp, stage_id="s9"))
        self.assertEqual(result.tool_calls, 0)

    def test_callable_behaviour_sees_the_request(self):
        seen = []
        harness = FakeHarness({"s1": lambda req: seen.append(req.attempt)})
        harness.run(request_for(self.tmp, attempt=2))
        self.assertEqual(seen, [2])

    def test_every_call_is_recorded(self):
        harness = FakeHarness()
        for attempt in (1, 2):
            harness.run(request_for(self.tmp, attempt=attempt))
        self.assertEqual([c.attempt for c in harness.calls], [1, 2])

    def test_tokens_are_nonzero_so_metrics_are_not_vacuous(self):
        harness = FakeHarness({"s1": [{"write": {"a": "b"}}]})
        self.assertGreater(harness.run(request_for(self.tmp)).tokens, 0)


class OpenCodeParsingTest(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_text()

    def test_tool_calls_are_counted(self):
        result = parse_opencode_stream(self.raw, 0, 4.0)
        self.assertEqual(result.tool_calls, 2)

    def test_tools_are_named(self):
        events = parse_opencode_stream(self.raw, 0, 4.0).events
        tools = [e.get("tool") for e in events if e["type"] == "tool.call"]
        self.assertEqual(tools, ["read", "edit"])

    def test_tokens_are_summed_across_steps(self):
        result = parse_opencode_stream(self.raw, 0, 4.0)
        self.assertEqual(result.tokens, 8444 + 120 + 12 + 9000 + 60 + 9200 + 30)

    def test_final_text_is_the_assistant_message(self):
        self.assertIn("fixed the spelling", parse_opencode_stream(self.raw, 0, 4.0).text)

    def test_step_finish_reasons_are_kept(self):
        reasons = [e["reason"] for e in parse_opencode_stream(self.raw, 0, 4.0).events
                   if e["type"] == "step.finish"]
        self.assertEqual(reasons, ["tool-calls", "tool-calls", "stop"])

    def test_event_input_is_shrunk_not_stored_whole(self):
        events = parse_opencode_stream(self.raw, 0, 4.0).events
        self.assertTrue(all(len(json.dumps(e)) < 600 for e in events))

    def test_garbage_lines_are_ignored(self):
        result = parse_opencode_stream("not json\n{oops\n" + self.raw, 0, 1.0)
        self.assertEqual(result.tool_calls, 2)

    def test_nonzero_exit_records_stderr_as_the_error(self):
        result = parse_opencode_stream("", 1, 1.0, "opencode: provider auth failed")
        self.assertFalse(result.ok)
        self.assertIn("auth failed", result.error)

    def test_empty_stream_is_not_a_crash(self):
        result = parse_opencode_stream("", 0, 1.0)
        self.assertEqual(result.tool_calls, 0)
        self.assertEqual(result.text, "")

    def test_raw_stream_is_kept_for_the_transcript(self):
        self.assertIn("step_start", parse_opencode_stream(self.raw, 0, 1.0).raw)


class OpenCodeDeadlineTest(unittest.TestCase):
    def test_timeout_stops_the_private_worker_and_keeps_its_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # A worker that outlives its CLI retains the lock and can still
            # write solutions or compete with the next stage for inference.
            (root / "worker.py").write_text(textwrap.dedent("""\
                import fcntl
                import time
                from pathlib import Path
                with Path("lease").open("w") as lease:
                    fcntl.flock(lease, fcntl.LOCK_EX)
                    Path("ready").touch()
                    time.sleep(8)
            """))
            binary = root / "cli"
            binary.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json
                import os
                import subprocess
                import sys
                import time
                from pathlib import Path
                assert "--standalone" in sys.argv
                assert os.environ["OPENCODE_DB"] == ":memory:"
                paths = [Path(os.environ[key]) for key in ("XDG_DATA_HOME", "XDG_STATE_HOME")]
                for path in paths:
                    path.mkdir(parents=True, exist_ok=True)
                    (path / "session").touch()
                Path("storage.json").write_text(json.dumps([str(p) for p in paths]))
                subprocess.Popen([sys.executable, "worker.py"])
                while not Path("ready").exists():
                    time.sleep(0.01)
                print(json.dumps({"type": "step_finish", "part": {"tokens": {"output": 7}}}), flush=True)
                time.sleep(8)
            """))
            binary.chmod(0o755)
            request = request_for(root)
            request.timeout_s = 1
            with patch.dict(os.environ, OPENCODE_DB=str(root / "personal.db"),
                            XDG_DATA_HOME=str(root / "data"), XDG_STATE_HOME=str(root / "state")):
                result = OpenCodeAdapter(bin_path=str(binary)).run(request)
            self.assertTrue(result.timed_out)
            self.assertEqual((result.exit_code, result.tokens), (124, 7))
            for location in json.loads((root / "storage.json").read_text()):
                self.assertFalse(Path(location).exists())
            self.assertFalse((root / "data").exists())
            self.assertFalse((root / "state").exists())
            with (root / "lease").open() as lease:
                deadline = time.monotonic() + 1
                while True:
                    try:
                        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            self.fail("OpenCode worker retained the workspace after its deadline")
                        time.sleep(0.01)


class AdapterPlumbingTest(unittest.TestCase):
    def test_registry_resolves_both_adapters(self):
        self.assertIsInstance(create("fake"), FakeHarness)
        self.assertIsInstance(create("opencode"), OpenCodeAdapter)

    def test_unknown_adapter_is_a_clear_error(self):
        with self.assertRaises(ValueError):
            create("no-such-harness")

    def test_registry_reports_availability_without_raising(self):
        report = available_harnesses()
        self.assertTrue(report["fake"][0])
        self.assertIn("opencode", report)

    def test_label_names_the_real_model_when_overridden(self):
        self.assertEqual(OpenCodeAdapter(model="acme/gpt-9").label(), "acme/gpt-9")

    def test_default_label_reports_the_configured_default(self):
        self.assertIn("(", OpenCodeAdapter().label())

    def test_default_model_resolution_never_raises(self):
        self.assertTrue(resolve_default_model())

    def test_missing_binary_is_reported_not_raised(self):
        usable, why = OpenCodeAdapter(bin_path="definitely-not-a-binary").available()
        self.assertFalse(usable)
        self.assertIn("not on PATH", why)


if __name__ == "__main__":
    unittest.main()
