"""Core agent loop: LLM reasoning + tool/command execution.

The agent uses an OpenAI-compatible chat completions API with a single tool
named ``run_command``.  The model decides which shell commands to run; the
agent executes them (after optional user confirmation) and feeds the output
back until the model produces a final answer.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .config import Settings
from .executor import CommandResult, run_command
from .safety import SafetyVerdict, assess


SYSTEM_PROMPT = """\
You are AITA, an AI terminal agent running on Windows 11.
You help the user accomplish tasks by running shell commands on their machine.

Environment:
- OS: Windows 11
- Default shell: cmd.exe (you may also propose PowerShell commands by prefixing with `powershell -Command "..."` or by using powershell cmdlets the agent will route them correctly)
- Working directory: {cwd}

Rules:
1. Use the `run_command` tool to execute commands. One command per tool call.
2. Prefer non-destructive, read-only commands first to gather information.
3. Keep commands simple and correct for Windows. Use `dir`, `type`, `where`, `findstr`, `tasklist` etc. for cmd. Use PowerShell cmdlets when more powerful.
4. Never run a command that deletes user data, formats drives, edits the registry, shuts down the machine, or installs software from untrusted sources without first explaining the risk and letting the user confirm.
5. After you have enough information, stop calling tools and write a concise final answer to the user summarizing what you did and the result.
6. If a command fails, read the error, fix the command, and try again. Do not repeat the exact same failing command.
7. Do not invent command output. Only rely on tool results.
"""


# The JSON schema for the single tool we expose to the model.
TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Run a shell command on the user's Windows machine and return "
            "stdout, stderr, and the exit code. Use this to inspect the "
            "system, run builds, manage files, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact command line to execute.",
                },
                "shell": {
                    "type": "string",
                    "enum": ["cmd", "powershell"],
                    "description": "Which shell to use. Defaults to cmd.",
                },
            },
            "required": ["command"],
        },
    },
}


ConfirmFn = Callable[[str, SafetyVerdict], bool]


@dataclass
class AgentEvent:
    """A single step emitted by the agent loop, for UI rendering."""

    kind: str  # "command" | "output" | "answer" | "error" | "info"
    text: str
    extra: dict[str, Any] = field(default_factory=dict)


class Agent:
    """Stateful agent that drives the LLM + command execution loop."""

    def __init__(
        self,
        settings: Settings,
        *,
        cwd: Path | str | None = None,
        confirm: ConfirmFn | None = None,
        max_steps: int = 25,
    ) -> None:
        self.settings = settings
        self.cwd = Path(cwd).resolve() if cwd else Path.cwd()
        self.confirm = confirm or (lambda _cmd, _v: True)
        self.max_steps = max_steps

        # Lazy import so the rest of the package works without openai installed.
        from openai import OpenAI  # type: ignore

        client_kwargs: dict[str, Any] = {"api_key": settings.api_key}
        if settings.base_url:
            client_kwargs["base_url"] = settings.base_url
        self.client = OpenAI(**client_kwargs)

        self.history: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(cwd=self.cwd),
            }
        ]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run(self, user_input: str):
        """Run one user turn. Yields :class:`AgentEvent` objects."""
        self.history.append({"role": "user", "content": user_input})

        steps = 0
        while steps < self.max_steps:
            steps += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.model,
                    messages=self.history,
                    tools=[TOOL_SCHEMA],
                    tool_choice="auto",
                    temperature=self.settings.temperature,
                )
            except Exception as exc:
                yield AgentEvent("error", f"LLM request failed: {exc}")
                return

            msg = response.choices[0].message
            self.history.append(msg.model_dump(exclude_none=True))

            tool_calls = msg.tool_calls or []
            if tool_calls:
                if msg.content:
                    yield AgentEvent("info", msg.content)
            else:
                # No tool calls -> the model is giving a final answer.
                yield AgentEvent("answer", msg.content or "")
                return

            for call in tool_calls:
                yield from self._handle_tool_call(call)

        yield AgentEvent(
            "error",
            f"Reached the maximum number of steps ({self.max_steps}) without a final answer.",
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _handle_tool_call(self, call):
        name = call.function.name
        if name != "run_command":
            yield AgentEvent("error", f"Unknown tool: {name}")
            self.history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"error": f"Unknown tool: {name}"}),
                }
            )
            return

        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            yield AgentEvent("error", f"Bad tool arguments: {exc}")
            self.history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"error": f"Bad arguments: {exc}"}),
                }
            )
            return

        command = str(args.get("command", "")).strip()
        shell = str(args.get("shell", "cmd")).strip().lower()
        if shell not in ("cmd", "powershell"):
            shell = "cmd"

        if not command:
            yield AgentEvent("error", "Model returned an empty command.")
            self.history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"error": "empty command"}),
                }
            )
            return

        verdict = assess(command)
        yield AgentEvent("command", command, {"shell": shell, "verdict": verdict})

        if not self.confirm(command, verdict):
            denied = "User denied execution of this command."
            yield AgentEvent("info", denied)
            self.history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"denied": True, "note": denied}),
                }
            )
            return

        result: CommandResult = run_command(
            command, cwd=self.cwd, shell=shell
        )
        yield AgentEvent(
            "output",
            result.combined_output(),
            {"returncode": result.returncode, "ok": result.ok},
        )

        self.history.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(
                    {
                        "returncode": result.returncode,
                        "stdout": result.stdout[:4000],
                        "stderr": result.stderr[:4000],
                        "timed_out": result.timed_out,
                    }
                ),
            }
        )