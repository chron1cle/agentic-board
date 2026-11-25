"""Run a fresh T3 Code thread through the t3code-threads client."""

from __future__ import annotations

import time

from .adapters import model_args
from .base import HarnessResult, elapsed
from .process import ProcessAdapter, execute, json_object


class T3CodeAdapter(ProcessAdapter):
    name = "t3code"
    executables = ("t3code-threads",)

    def run(self, request):
        binary = self.binary()
        if not binary:
            return HarnessResult(exit_code=127, error=self.available()[1])

        started = time.monotonic()
        workspace = request.workspace.resolve()
        created = execute(
            [binary, "new", "--cwd", str(workspace), "--json",
             "--runtime-mode", "auto-accept-edits", *model_args(request.model or self.model)],
            workspace, request.timeout_s,
        )
        thread = json_object(created.raw).get("threadId")
        if not created.ok:
            return created
        if not isinstance(thread, str) or not thread or thread.startswith("-"):
            created.error = "T3 Code did not return a thread ID"
            return created

        remaining = request.timeout_s - (time.monotonic() - started)
        try:
            result = HarnessResult(exit_code=124, timed_out=True) if remaining <= 0 else execute(
                [binary, "send", thread, request.prompt, "--json"], workspace, remaining,
            )
        finally:
            # The provider process belongs to the server.
            stopped = execute([binary, "stop", thread], workspace, 5)
        result.seconds = elapsed(started)
        result.tools_reported = result.tokens_reported = False
        payload = json_object(result.raw)
        if not stopped.ok:
            result.timed_out = False
            result.error = "T3 Code provider session could not be stopped"
        elif result.ok and payload.get("status") != "completed":
            result.error = "T3 Code did not report a completed turn"

        responses = payload.get("assistantResponses")
        if isinstance(responses, list):
            texts = [response.get("text") if isinstance(response, dict) else response for response in responses]
            result.text = "\n".join(text for text in texts if isinstance(text, str))
        return result
