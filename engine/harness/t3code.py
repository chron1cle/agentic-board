"""Run a single thread on an attempt-owned T3 server."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from .adapters import model_args
from .base import HarnessResult
from .process import ProcessAdapter, execute, json_object
from .profile import attempt_environment


class T3CodeAdapter(ProcessAdapter):
    name = "t3code"
    executables = ("t3code-threads",)

    def available(self):
        if not shutil.which("t3"):
            return False, "t3 is required to start a private benchmark server"
        return super().available()

    def run(self, request):
        client = self.binary()
        server = shutil.which("t3")
        if not client or not server:
            return HarnessResult(exit_code=127, error="T3 benchmarks require t3 and t3code-threads")
        with attempt_environment(self.name) as (env, profile):
            result = execute(
                [sys.executable, "-IS", str(Path(__file__).with_name("_t3server.py")),
                 server, client, *model_args(request.model or self.model)],
                request.workspace, request.timeout_s, stdin=request.prompt, env=env, profile=profile,
            )
        result.tools_reported = result.tokens_reported = False
        payload = json_object(result.raw)
        if result.ok and payload.get("status") != "completed":
            result.error = "T3 Code did not report a completed turn"
        responses = payload.get("assistantResponses")
        if isinstance(responses, list):
            result.text = "\n".join(item["text"] for item in responses if isinstance(item, dict)
                                    and isinstance(item.get("text"), str))
        return result
