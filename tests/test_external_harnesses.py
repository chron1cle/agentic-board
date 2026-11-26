"""Protocol and subprocess regressions with synthetic output and no provider."""

import json
import os
import subprocess
import sys
import textwrap
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.harness import REGISTRY, create
from engine.harness.base import HarnessRequest, HarnessResult


class ExternalHarnessTest(unittest.TestCase):
    def test_native_protocols(self):
        cases = {
            "codex": [
                {"type": "item.started", "item": {"id": "one", "type": "command_execution"}},
                {"type": "item.completed", "item": {"id": "one", "type": "command_execution"}},
                {"type": "turn.completed", "usage": {"input_tokens": 7, "output_tokens": 3,
                                                        "cached_input_tokens": 5}},
            ],
            "cline": [
                {"type": "agent_event", "event": {"type": "content_end", "content": {
                    "type": "tool_use", "name": "read", "id": "one"}}},
                {"type": "run_result", "finishReason": "completed", "usage": {
                    "inputTokens": 7, "outputTokens": 3}},
            ],
            "kilo": [
                {"type": "tool_use", "part": {"tool": "read"}},
                {"type": "step_finish", "part": {"tokens": {"input": 7, "output": 3}}},
            ],
            "grokbuild": [
                {"type": "tool_call", "toolCallId": "one", "toolName": "read"},
                {"type": "tool_call_update", "toolCallId": "one"},
                {"type": "usage", "usage": {"input_tokens": 7, "output_tokens": 3}},
                {"type": "end", "stopReason": "end_turn", "usage": {"total_tokens": 10}},
            ],
            "antigravity": [
                {"event": "step_update", "step_update": {"step_type": "tool", "step_index": 2,
                                                        "tool_name": "read", "state": "ACTIVE"}},
                {"event": "step_update", "step_update": {"step_type": "tool", "step_index": 2,
                                                        "tool_name": "read", "state": "DONE"}},
                {"event": "result", "result": {"status": "SUCCESS", "usage": {"total_tokens": 10}}},
            ],
            "pi": [
                {"type": "tool_execution_start", "toolCallId": "one", "toolName": "read"},
                {"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
                                                     "usage": {"totalTokens": 10}, "content": []}},
                {"type": "agent_end"},
            ],
            "hermes": [
                {"type": "tool_use", "name": "read"},
                {"type": "result", "exit_code": 0, "tokens": {"total": 10}},
            ],
        }
        for name, events in cases.items():
            with self.subTest(name=name):
                result = HarnessResult(raw="".join(json.dumps(event) + "\n" for event in events))
                adapter = create(name)
                adapter.read(result)
                self.assertTrue(result.ok, result.error)
                self.assertEqual((result.tool_calls, result.tokens), (1, 10))
                empty = HarnessResult()
                adapter.read(empty)
                self.assertFalse(empty.ok)

    def test_generic_command_receives_exact_prompt_and_attempt_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            workspace = parent / "workspace"
            workspace.mkdir()
            binary = parent / "wrapper"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "from pathlib import Path\n"
                "request = json.load(sys.stdin)\n"
                "Path('received.json').write_text(json.dumps(request))\n"
                "print(json.dumps({'type':'tool.call','tool':'write'}))\n"
                "print(json.dumps({'type':'result','ok':True,'tokens':13}))\n"
            )
            binary.chmod(0o700)
            request = HarnessRequest('A multi-line prompt.\n"Keep quotes".', workspace, 5,
                                     stage_id="stage", attempt=2, model="synthetic")
            result = create("command", bin_path=str(binary)).run(request)
            received = json.loads((workspace / "received.json").read_text())
            self.assertEqual(received["prompt"], request.prompt)
            self.assertEqual(received["model"], "synthetic")
            self.assertEqual(received["attempt"], 2)
            self.assertTrue(result.ok, result.error)
            self.assertEqual((result.tool_calls, result.tokens), (1, 13))

    def test_external_attempts_get_fresh_storage_even_with_parent_overrides(self):
        storage = {"opencode": "XDG_DATA_HOME", "kilo": "KILO_DB", "cline": "CLINE_DATA_DIR",
                   "grokbuild": "GROK_HOME", "codex": "CODEX_HOME", "pi": "PI_CODING_AGENT_DIR",
                   "hermes": "HERMES_HOME", "antigravity": "ANTIGRAVITY_APP_DATA_DIR", "command": "HOME"}
        self.assertEqual(set(storage) | {"fake", "solve", "t3code"}, set(REGISTRY))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            personal = root / "personal"
            personal.mkdir()
            (personal / "previous-session").touch()
            inherited = dict.fromkeys(storage.values(), str(personal))
            inherited.update(OPENCODE_DB=str(personal / "db"), KILO_NO_DAEMON="",
                             CLINE_SESSION_BACKEND_MODE="hub", GROK_LEADER_SOCKET=str(personal / "sock"))
            for name, key in storage.items():
                seen = []
                def check(argv, workspace, timeout, *, env, profile, stdin=None):
                    self.assertTrue(Path(env[key]).is_relative_to(profile))
                    self.assertNotIn(str(personal), (env["XDG_DATA_HOME"], env["XDG_STATE_HOME"]))
                    self.assertEqual(env["OPENCODE_DB"], ":memory:")
                    self.assertEqual(env["KILO_NO_DAEMON"], "1")
                    self.assertEqual(env["CLINE_SESSION_BACKEND_MODE"], "local")
                    flags = {"opencode": "--standalone", "codex": "--ephemeral", "pi": "--no-session",
                             "cline": "--data-dir", "grokbuild": "--leader-socket",
                             "antigravity": "--remote-agent=false", "hermes": "--oneshot"}
                    if name in flags:
                        self.assertIn(flags[name], argv)
                    self.assertTrue(Path(env["GROK_LEADER_SOCKET"]).is_relative_to(profile))
                    (profile / "broken-session").touch()
                    seen.append(profile)
                    return HarnessResult(exit_code=1, error="synthetic interruption")

                target = "opencode" if name == "opencode" else "process"
                with self.subTest(name=name), patch.dict(os.environ, inherited), patch(
                    f"engine.harness.{target}.execute", side_effect=check,
                ):
                    adapter = create(name, bin_path=sys.executable)
                    for _ in range(2):
                        self.assertFalse(adapter.run(HarnessRequest("task", root, 2)).ok)
                    self.assertEqual(len(set(seen)), 2)
                    self.assertFalse(any(path.exists() for path in seen))
            self.assertEqual([p.name for p in personal.iterdir()], ["previous-session"])

    def test_t3_uses_a_disposable_server_on_success_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server = root / "t3"
            server.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json, os, sys, time
                from pathlib import Path
                base = Path(sys.argv[sys.argv.index("--base-dir") + 1])
                if sys.argv[1] == "auth":
                    assert "--token-only" in sys.argv
                    print("test-only")
                else:
                    assert "--no-browser" in sys.argv and "--auto-bootstrap-project-from-cwd" in sys.argv
                    assert sys.argv[sys.argv.index("--host") + 1] == "127.0.0.1"
                    state = base / "userdata"
                    state.mkdir(parents=True)
                    (state / "server-runtime.json").write_text(json.dumps({"port": 12345, "pid": os.getpid()}))
                    time.sleep(30)
            """))
            client = root / "t3code-threads"
            client.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json, os, sys, time
                from pathlib import Path
                config = Path(sys.argv[sys.argv.index("--config") + 1])
                assert json.loads(config.read_text())["servers"]["benchmark"]["httpUrl"] == "http://127.0.0.1:12345"
                assert os.environ["T3_ATTEMPT_TOKEN"] == "test-only"
                assert sys.argv.count("new") == 1 and "send" not in sys.argv
                Path("server-home").write_text(str(config.parent))
                if sys.argv[-1] == "timeout":
                    time.sleep(30)
                print(json.dumps({"status":"completed","assistantResponses":[{"text":"done"}]}))
            """))
            server.chmod(0o700)
            client.chmod(0o700)
            with patch.dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"]):
                for prompt, timeout in (("finish", 5), ("timeout", 1)):
                    with self.subTest(prompt=prompt):
                        result = create("t3code").run(HarnessRequest(prompt, root, timeout))
                        self.assertEqual(result.timed_out, prompt == "timeout", result.error)
                        if prompt == "finish":
                            self.assertTrue(result.ok, result.error)
                            self.assertEqual(result.text, "done")
                        self.assertFalse(Path((root / "server-home").read_text()).exists())
                        self.assertFalse(result.tokens_reported)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux detached-worker supervision")
    def test_cli_exit_reaps_detached_children_on_success_and_failure(self):
        from engine.harness.process import execute

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = textwrap.dedent("""
                import subprocess, sys
                from pathlib import Path
                child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                         start_new_session=True)
                Path("worker").write_text(str(child.pid))
                sys.exit(int(sys.argv[1]))
            """)
            for code in (0, 7):
                with self.subTest(code=code):
                    result = execute([sys.executable, "-c", script, str(code)], root, 3)
                    self.assertEqual(result.exit_code, code)
                    self.assertFalse(result.timed_out)
                    self.assertFalse((Path("/proc") / (root / "worker").read_text()).exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux detached-worker supervision")
    def test_killing_engine_reaps_detached_worker_and_discards_its_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrapper = root / "wrapper"
            wrapper.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json, os, subprocess, sys, time
                from pathlib import Path
                child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                         start_new_session=True)
                Path("ready.tmp").write_text(json.dumps([os.getpid(), child.pid, os.environ["HOME"]]))
                Path("ready.tmp").rename("ready")
                time.sleep(30)
            """))
            wrapper.chmod(0o700)
            code = ("from pathlib import Path\nfrom engine.harness import create\n"
                    "from engine.harness.base import HarnessRequest\nimport sys\n"
                    "root = Path(sys.argv[1])\n"
                    "create('command', bin_path=str(root/'wrapper')).run(HarnessRequest('task', root, 30))")
            with subprocess.Popen([sys.executable, "-c", code, str(root)],
                                  cwd=Path(__file__).resolve().parents[1]) as engine:
                try:
                    deadline = time.monotonic() + 5
                    while not (root / "ready").exists() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    cli_pid, worker_pid, home = json.loads((root / "ready").read_text())
                finally:
                    engine.kill()
                    engine.wait()
            paths = [Path(f"/proc/{pid}") for pid in (cli_pid, worker_pid)] + [Path(home)]
            deadline = time.monotonic() + 3
            while any(p.exists() for p in paths) and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertFalse([p for p in paths if p.exists()])
