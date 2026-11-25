"""Headless adapters for coding CLIs and compatible general agents."""

from __future__ import annotations

import json
import os

from .base import HarnessResult
from .opencode import parse_opencode_stream
from .process import ProcessAdapter, ToolEvents, object_value, objects, token_count


def model_args(model):
    return ["--model", model] if model else []


def read_usage(result, usage, totals, components, *, accumulate=False):
    tokens = token_count(usage, totals, components)
    if tokens is not None:
        result.tokens = result.tokens + tokens if accumulate else tokens
        result.tokens_reported = True


def require_completion(result, done, name):
    if not done and result.ok:
        result.error = f"{name} did not report a completed attempt"


def set_text(result, text):
    if isinstance(text, str):
        result.text = text


class CodexAdapter(ProcessAdapter):
    name = "codex"
    executables = ("codex",)

    def invocation(self, request, model):
        return (["exec", "--json", "--ephemeral", "--skip-git-repo-check",
                 "--sandbox", "workspace-write", "-c", 'approval_policy="never"',
                 *model_args(model), "-"], request.prompt, None)

    def read(self, result):
        tools = ToolEvents(result)
        done = False
        for event in objects(result.raw):
            kind = event.get("type")
            if kind in {"item.started", "item.completed"}:
                item = object_value(event.get("item"))
                item_type = item.get("type")
                if item_type in {"command_execution", "file_change", "mcp_tool_call",
                                 "web_search", "collab_tool_call", "dynamic_tool_call"}:
                    tools.add(item.get("tool", item_type), item.get("id"))
                elif kind == "item.completed" and item_type == "agent_message":
                    set_text(result, item.get("text"))
            elif kind == "turn.completed":
                done = True
                read_usage(result, event.get("usage"), (), ("input_tokens", "output_tokens"))
            elif kind == "turn.failed":
                result.error = "Codex turn failed"
        require_completion(result, done, "Codex")


class KiloAdapter(ProcessAdapter):
    name = "kilo"
    executables = ("kilo",)

    def invocation(self, request, model):
        return ["run", "--auto", "--format", "json", *model_args(model)], request.prompt, None

    def read(self, result):
        parsed = parse_opencode_stream(result.raw, result.exit_code, result.seconds)
        result.tool_calls, result.tokens = parsed.tool_calls, parsed.tokens
        result.events, result.text = parsed.events, parsed.text
        result.tokens_reported = any(
            event.get("type") == "step_finish" and object_value(event.get("part")).get("tokens")
            for event in objects(result.raw)
        )
        if result.exit_code == 124:
            result.timed_out = True
        if parsed.error:
            result.error = "Kilo reported a session error"
        require_completion(result, any(event.get("type") == "step.finish" for event in result.events), "Kilo")


class ClineAdapter(ProcessAdapter):
    name = "cline"
    executables = ("cline",)

    def invocation(self, request, model):
        provider, sep, identifier = model.partition("/") if model else ("", "", "")
        selection = ["--provider", provider, "--model", identifier] if sep else model_args(model)
        return (["--json", "--auto-approve", "true", *selection, request.prompt], None,
                {**os.environ, "CLINE_SESSION_BACKEND_MODE": "local"})

    def read(self, result):
        done = False
        tools = ToolEvents(result)
        result.tools_reported = False
        for event in objects(result.raw):
            kind = event.get("type")
            if kind == "agent_event":
                inner = object_value(event.get("event"))
                content = object_value(inner.get("content") or inner.get("block"))
                if inner.get("type") == "content_end" and content.get("type") in {"tool_call", "tool_use", "toolCall"}:
                    tools.add(content.get("name", content.get("toolName")), content.get("id", content.get("toolCallId")))
                    result.tools_reported = True
                elif inner.get("type") == "usage":
                    read_usage(result, inner, (), ("totalInputTokens", "totalOutputTokens",
                                                   "totalCacheReadTokens", "totalCacheWriteTokens"))
            elif kind == "run_result":
                done = event.get("finishReason") == "completed"
                calls = event.get("toolCalls")
                if isinstance(calls, list):
                    for call in calls:
                        if isinstance(call, dict):
                            tools.add(call.get("name", call.get("toolName")), call.get("id", call.get("toolCallId")))
                    result.tool_calls = len(calls)
                    result.tools_reported = True
                set_text(result, event.get("text"))
                read_usage(result, event.get("usage"), ("totalTokens", "total_tokens", "total"),
                           ("inputTokens", "outputTokens", "cacheReadTokens", "cacheWriteTokens"))
            elif kind == "run_aborted":
                result.error = "Cline run aborted"
        require_completion(result, done, "Cline")


class GrokBuildAdapter(ProcessAdapter):
    name = "grokbuild"
    executables = ("grok",)

    def invocation(self, request, model):
        return (["--output-format", "streaming-json", "--always-approve", "--no-memory",
                 "--disable-web-search", *model_args(model), "--single", request.prompt], None, None)

    def read(self, result):
        tools = ToolEvents(result)
        chunks = []
        done = False
        for event in objects(result.raw):
            kind = event.get("type")
            if kind == "tool_call":
                tools.add(event.get("toolName"), event.get("toolCallId"))
            elif kind == "text" and isinstance(event.get("data"), str):
                chunks.append(event["data"])
            elif kind in {"usage", "end", "error"}:
                read_usage(result, event.get("usage"), ("total_tokens",),
                           ("input_tokens", "output_tokens", "cache_read_input_tokens",
                            "cache_creation_input_tokens"), accumulate=kind == "usage")
                if kind == "end":
                    done = event.get("stopReason") not in {"cancelled", "refusal"}
                elif kind == "error":
                    result.error = "Grok Build turn failed"
        result.text = "".join(chunks)
        require_completion(result, done, "Grok Build")


class AntigravityAdapter(ProcessAdapter):
    name = "antigravity"
    executables = ("agy", "antigravity")

    def invocation(self, request, model):
        return (["--output-format", "stream-json", "--mode", "auto", "--sandbox",
                 "--disable-slash-commands", *model_args(model), "--print", request.prompt], None, None)

    def read(self, result):
        tools = ToolEvents(result)
        done = False
        for event in objects(result.raw):
            if event.get("event") == "step_update":
                step = object_value(event.get("step_update"))
                if step.get("step_type") == "tool" and step.get("tool_name"):
                    tools.add(step["tool_name"], step.get("step_index"))
            elif event.get("event") == "result":
                final = object_value(event.get("result"))
                done = final.get("status") == "SUCCESS"
                set_text(result, final.get("response"))
                read_usage(result, final.get("usage"), ("total_tokens",), ("input_tokens", "output_tokens"))
        require_completion(result, done, "Antigravity")


class PiAdapter(ProcessAdapter):
    name = "pi"
    executables = ("pi",)

    def invocation(self, request, model):
        return ["--mode", "json", "--no-session", *model_args(model), request.prompt], None, None

    def read(self, result):
        tools = ToolEvents(result)
        done = False
        stop = None
        for event in objects(result.raw):
            if event.get("type") == "tool_execution_start":
                tools.add(event.get("toolName"), event.get("toolCallId"))
            elif event.get("type") == "message_end":
                message = object_value(event.get("message"))
                if message.get("role") != "assistant":
                    continue
                stop = message.get("stopReason")
                read_usage(result, message.get("usage"), ("totalTokens",),
                           ("input", "output", "cacheRead", "cacheWrite"), accumulate=True)
                result.text = "".join(
                    block["text"] for block in message.get("content", [])
                    if isinstance(block, dict) and block.get("type") == "text"
                    and isinstance(block.get("text"), str))
            elif event.get("type") == "agent_end":
                done = True
        require_completion(result, done and stop not in {None, "error", "aborted"}, "Pi")


class HermesAdapter(ProcessAdapter):
    name = "hermes"
    executables = ("hermes",)

    def invocation(self, request, model):
        return (["chat", "--oneshot", "--format", "stream-json", "--toolsets", "terminal,file",
                 *model_args(model), "--query", request.prompt], None,
                {**os.environ, "TERMINAL_ENV": "local", "TERMINAL_CWD": str(request.workspace.resolve())})

    def read(self, result):
        tools = ToolEvents(result)
        done = False
        for event in objects(result.raw):
            if event.get("type") == "tool_use":
                tools.add(event.get("name"), event.get("id"))
            elif event.get("type") == "result":
                done = event.get("exit_code") == 0 and not event.get("error") and not event.get("replay_gap")
                set_text(result, event.get("text"))
                read_usage(result, event.get("tokens"), ("total",), ("input", "output"))
        require_completion(result, done, "Hermes")


class CommandAdapter(ProcessAdapter):
    """Run an operator-supplied executable using the board's stdin/stdout contract."""

    name = "command"

    def available(self):
        if not self.bin_path:
            return False, "command requires --harness-bin PATH"
        return super().available()

    def invocation(self, request, model):
        return [], json.dumps({
            "prompt": request.prompt, "model": model, "stage_id": request.stage_id,
            "attempt": request.attempt, "timeout_s": request.timeout_s,
        }) + "\n", None

    def read(self, result):
        final = None
        tools = ToolEvents(result)
        for event in objects(result.raw):
            if event.get("type") == "tool.call":
                tools.add(event.get("tool"), event.get("id"))
            elif event.get("type") == "result":
                if final is not None:
                    result.error = "command emitted more than one terminal result"
                final = event
        if final:
            set_text(result, final.get("text"))
            read_usage(result, final, ("tokens",), ())
        require_completion(result, final is not None and final.get("ok") is True
                           and result.tokens_reported, "command")
