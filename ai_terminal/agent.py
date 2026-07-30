"""Core agent loop: LLM reasoning + tool/command execution.

The agent uses an OpenAI-compatible chat completions API with several tools:

* ``run_command`` — execute a shell command
* ``read_file`` — read a file from disk
* ``write_file`` — create or overwrite a file
* ``edit_file`` — search-and-replace within a file
* ``list_files`` — list directory contents

The model decides which tools to call; the agent executes them (after
optional user confirmation for dangerous commands) and feeds the output
back until the model produces a final answer.
"""

from __future__ import annotations

import json
import logging
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generator

from .config import Settings
from .executor import CommandResult, run_command
from .safety import SafetyVerdict, assess
from .tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — cross-platform
# ---------------------------------------------------------------------------

_OS_INFO = f"{platform.system()} {platform.release()} ({platform.machine()})"

SYSTEM_PROMPT = """\
You are a helpful AI coding agent running on the user's machine.
You help the user accomplish tasks by running shell commands, reading and
writing files, and providing clear explanations.

Environment:
- OS: {os_info}
- Default shell: {default_shell}
- Working directory: {cwd}

Available tools:
- run_command — execute a shell command and return stdout/stderr/exit code
- read_file — read a file's contents
- write_file — create or overwrite a file (parent dirs created automatically)
- edit_file — search-and-replace within a file (surgical edits)
- list_files — list directory contents

Rules:
1. Use the available tools to accomplish the user's request. One action per \
tool call.
2. Prefer non-destructive, read-only operations first to gather information.
3. Use the correct shell syntax for the detected OS. On Unix use bash/sh \
commands; on Windows use cmd/PowerShell.
4. Never run a command that deletes user data, formats drives, edits \
critical system config, shuts down the machine, or installs software \
from untrusted sources without first explaining the risk and letting the \
user confirm.
5. After you have enough information, stop calling tools and write a concise \
final answer summarizing what you did and the result.
6. If a command fails, read the error, fix it, and try again. Do not repeat \
the exact same failing command.
7. Do not invent command output. Only rely on tool results.
8. When writing code, follow best practices: proper error handling, clear \
naming, comments where helpful, and idiomatic style for the language.
"""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ConfirmFn = Callable[[str, SafetyVerdict], bool]


@dataclass
class AgentEvent:
    """A single step emitted by the agent loop, for UI rendering."""

    kind: str  # "command" | "output" | "answer" | "error" | "info" | "file_op"
    text: str
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    """Stateful agent that drives the LLM + tool execution loop."""

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

        # Lazy import so the rest of the package works without openai.
        from openai import OpenAI  # type: ignore[import-untyped]

        client_kwargs: dict[str, Any] = {"api_key": settings.api_key}
        if settings.base_url:
            client_kwargs["base_url"] = settings.base_url
        self.client = OpenAI(**client_kwargs)

        default_shell = "cmd" if platform.system() == "Windows" else "bash"

        self.history: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    os_info=_OS_INFO,
                    default_shell=default_shell,
                    cwd=self.cwd,
                ),
            }
        ]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self, user_input: str) -> Generator[AgentEvent, None, None]:
        """Run one user turn.  Yields :class:`AgentEvent` objects."""
        self.history.append({"role": "user", "content": user_input})

        steps = 0
        while steps < self.max_steps:
            steps += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.model,
                    messages=self.history,
                    tools=ALL_TOOLS,
                    tool_choice="auto",
                    temperature=self.settings.temperature,
                )
            except Exception as exc:
                logger.exception("LLM request failed")
                yield AgentEvent("error", f"LLM request failed: {exc}")
                return

            msg = response.choices[0].message
            self.history.append(msg.model_dump(exclude_none=True))

            tool_calls = msg.tool_calls or []
            if tool_calls:
                if msg.content:
                    yield AgentEvent("info", msg.content)
            else:
                # No tool calls → the model is giving a final answer.
                yield AgentEvent("answer", msg.content or "")
                return

            for call in tool_calls:
                yield from self._handle_tool_call(call)

        yield AgentEvent(
            "error",
            f"Reached the maximum number of steps ({self.max_steps}) "
            f"without a final answer.",
        )

    # ------------------------------------------------------------------ #
    # Tool dispatch
    # ------------------------------------------------------------------ #

    def _handle_tool_call(
        self, call: Any
    ) -> Generator[AgentEvent, None, None]:
        name = call.function.name

        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            yield AgentEvent("error", f"Bad tool arguments: {exc}")
            self._append_tool_result(call.id, {"error": f"Bad arguments: {exc}"})
            return

        handler = {
            "run_command": self._tool_run_command,
            "read_file": self._tool_read_file,
            "write_file": self._tool_write_file,
            "edit_file": self._tool_edit_file,
            "list_files": self._tool_list_files,
        }.get(name)

        if handler is None:
            yield AgentEvent("error", f"Unknown tool: {name}")
            self._append_tool_result(call.id, {"error": f"Unknown tool: {name}"})
            return

        yield from handler(call.id, args)

    # ------------------------------------------------------------------ #
    # Tool: run_command
    # ------------------------------------------------------------------ #

    def _tool_run_command(
        self, call_id: str, args: dict[str, Any]
    ) -> Generator[AgentEvent, None, None]:
        command = str(args.get("command", "")).strip()
        shell = str(args.get("shell", "auto")).strip().lower()

        if not command:
            yield AgentEvent("error", "Model returned an empty command.")
            self._append_tool_result(call_id, {"error": "empty command"})
            return

        verdict = assess(command)
        yield AgentEvent(
            "command", command, {"shell": shell, "verdict": verdict}
        )

        if not self.confirm(command, verdict):
            denied = "User denied execution of this command."
            yield AgentEvent("info", denied)
            self._append_tool_result(call_id, {"denied": True, "note": denied})
            return

        result: CommandResult = run_command(
            command,
            cwd=self.cwd,
            shell=shell,
            timeout=self.settings.command_timeout,
        )
        yield AgentEvent(
            "output",
            result.combined_output(),
            {"returncode": result.returncode, "ok": result.ok},
        )

        self._append_tool_result(call_id, {
            "returncode": result.returncode,
            "stdout": result.stdout[:8000],
            "stderr": result.stderr[:4000],
            "timed_out": result.timed_out,
        })

    # ------------------------------------------------------------------ #
    # Tool: read_file
    # ------------------------------------------------------------------ #

    def _tool_read_file(
        self, call_id: str, args: dict[str, Any]
    ) -> Generator[AgentEvent, None, None]:
        raw_path = str(args.get("path", "")).strip()
        max_chars = int(args.get("max_chars", 8000))

        if not raw_path:
            yield AgentEvent("error", "read_file: no path provided.")
            self._append_tool_result(call_id, {"error": "no path"})
            return

        filepath = (self.cwd / raw_path).resolve()
        yield AgentEvent("file_op", f"READ {filepath}")

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_chars:
                content = (
                    content[:max_chars]
                    + f"\n...[truncated {len(content) - max_chars} chars]"
                )
            self._append_tool_result(call_id, {
                "path": str(filepath),
                "content": content,
                "size": filepath.stat().st_size,
            })
        except FileNotFoundError:
            yield AgentEvent("error", f"File not found: {filepath}")
            self._append_tool_result(call_id, {"error": f"File not found: {filepath}"})
        except Exception as exc:
            yield AgentEvent("error", f"read_file failed: {exc}")
            self._append_tool_result(call_id, {"error": str(exc)})

    # ------------------------------------------------------------------ #
    # Tool: write_file
    # ------------------------------------------------------------------ #

    def _tool_write_file(
        self, call_id: str, args: dict[str, Any]
    ) -> Generator[AgentEvent, None, None]:
        raw_path = str(args.get("path", "")).strip()
        content = str(args.get("content", ""))

        if not raw_path:
            yield AgentEvent("error", "write_file: no path provided.")
            self._append_tool_result(call_id, {"error": "no path"})
            return

        filepath = (self.cwd / raw_path).resolve()
        yield AgentEvent(
            "file_op",
            f"WRITE {filepath} ({len(content)} chars)",
        )

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            self._append_tool_result(call_id, {
                "path": str(filepath),
                "chars_written": len(content),
                "ok": True,
            })
        except Exception as exc:
            yield AgentEvent("error", f"write_file failed: {exc}")
            self._append_tool_result(call_id, {"error": str(exc)})

    # ------------------------------------------------------------------ #
    # Tool: edit_file
    # ------------------------------------------------------------------ #

    def _tool_edit_file(
        self, call_id: str, args: dict[str, Any]
    ) -> Generator[AgentEvent, None, None]:
        raw_path = str(args.get("path", "")).strip()
        old_text = str(args.get("old_text", ""))
        new_text = str(args.get("new_text", ""))

        if not raw_path:
            yield AgentEvent("error", "edit_file: no path provided.")
            self._append_tool_result(call_id, {"error": "no path"})
            return

        filepath = (self.cwd / raw_path).resolve()
        yield AgentEvent(
            "file_op",
            f"EDIT {filepath} (replace {len(old_text)} → {len(new_text)} chars)",
        )

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            yield AgentEvent("error", f"File not found: {filepath}")
            self._append_tool_result(call_id, {"error": f"File not found: {filepath}"})
            return
        except Exception as exc:
            yield AgentEvent("error", f"edit_file read failed: {exc}")
            self._append_tool_result(call_id, {"error": str(exc)})
            return

        if old_text not in content:
            yield AgentEvent(
                "error",
                f"edit_file: old_text not found in {filepath.name}",
            )
            self._append_tool_result(call_id, {
                "error": "old_text not found in file",
                "path": str(filepath),
            })
            return

        new_content = content.replace(old_text, new_text, 1)
        try:
            filepath.write_text(new_content, encoding="utf-8")
            self._append_tool_result(call_id, {
                "path": str(filepath),
                "ok": True,
                "replacements": 1,
            })
        except Exception as exc:
            yield AgentEvent("error", f"edit_file write failed: {exc}")
            self._append_tool_result(call_id, {"error": str(exc)})

    # ------------------------------------------------------------------ #
    # Tool: list_files
    # ------------------------------------------------------------------ #

    def _tool_list_files(
        self, call_id: str, args: dict[str, Any]
    ) -> Generator[AgentEvent, None, None]:
        raw_path = str(args.get("path", "")).strip() or "."
        recursive = bool(args.get("recursive", False))
        max_entries = int(args.get("max_entries", 200))

        dirpath = (self.cwd / raw_path).resolve()
        yield AgentEvent("file_op", f"LIST {dirpath} (recursive={recursive})")

        if not dirpath.is_dir():
            yield AgentEvent("error", f"Not a directory: {dirpath}")
            self._append_tool_result(call_id, {"error": f"Not a directory: {dirpath}"})
            return

        entries: list[str] = []
        try:
            if recursive:
                for p in sorted(dirpath.rglob("*")):
                    if len(entries) >= max_entries:
                        entries.append(f"... (truncated at {max_entries})")
                        break
                    rel = p.relative_to(dirpath)
                    suffix = "/" if p.is_dir() else ""
                    entries.append(f"{rel}{suffix}")
            else:
                for p in sorted(dirpath.iterdir()):
                    if len(entries) >= max_entries:
                        entries.append(f"... (truncated at {max_entries})")
                        break
                    suffix = "/" if p.is_dir() else ""
                    entries.append(f"{p.name}{suffix}")
        except PermissionError as exc:
            yield AgentEvent("error", f"Permission denied: {exc}")
            self._append_tool_result(call_id, {"error": str(exc)})
            return

        self._append_tool_result(call_id, {
            "path": str(dirpath),
            "entries": entries,
            "count": len(entries),
        })

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _append_tool_result(self, call_id: str, data: dict[str, Any]) -> None:
        self.history.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(data),
        })
