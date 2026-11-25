"""Protocol and subprocess regressions with synthetic output and no provider."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.harness import create
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

    def test_t3_stops_the_server_session_after_timeout(self):
        executor = [
            HarnessResult(raw='{"threadId":"fresh-thread"}'),
            HarnessResult(exit_code=124, timed_out=True),
            HarnessResult(),
        ]
        adapter = create("t3code")
        with patch.object(adapter, "binary", return_value="/bin/t3code-threads"), patch(
            "engine.harness.t3code.execute", side_effect=executor,
        ) as execute:
            result = adapter.run(HarnessRequest("task", Path("."), 5))
        self.assertTrue(result.timed_out)
        self.assertFalse(result.tools_reported)
        commands = [call.args[0] for call in execute.call_args_list]
        self.assertEqual([argv[1] for argv in commands], ["new", "send", "stop"])
        self.assertEqual(commands[-1][2], "fresh-thread")
