"""Core Tell loop: answer-only LLM conversations.

Tell uses an OpenAI-compatible chat completions API to answer questions in
plain language. Runtime execution is intentionally disabled: Tell does not
run shell commands, read local files, write files, or call tools on behalf
of the model.
"""

from __future__ import annotations

import logging
import platform
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — cross-platform
# ---------------------------------------------------------------------------

_OS_INFO = f"{platform.system()} {platform.release()} ({platform.machine()})"

SYSTEM_PROMPT = """\
You are Tell, a helpful answer-only terminal assistant.
You answer the user's questions clearly and safely from the conversation
context. You do not run commands, inspect local files, write files, edit
files, install packages, or operate the user's machine.

Environment hints for tailoring answers:
- OS: {os_info}
- Default shell: {default_shell}
- Working directory label: {cwd}

Rules:
1. Give direct answers only. Do not claim that you ran commands, read files,
   changed files, or verified local state.
2. If the user asks you to perform an action on their machine, explain that
   Tell is answer-only and provide safe instructions or commands they can run
   themselves.
3. If the answer depends on local files, logs, command output, or private
   project context you cannot see, ask the user to paste the relevant text or
   provide a command they can run to collect it.
4. Prefer concise, practical answers. Use Markdown when it improves clarity.
5. For commands you suggest, make risks explicit and prefer read-only commands
   first. Never suggest destructive commands without a clear warning.
6. Do not invent local facts, command output, file contents, test results, or
   repository state.

Mission-grade communication style:
- Be warm, confident, and plain-spoken.
- For simple questions, answer in a few sentences or bullets.
- For complex questions, use a compact "Answer" format with:
  - Summary
  - Details
  - Suggested next steps, only when useful
"""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class AgentEvent:
    """A single step emitted by the Tell loop, for UI rendering."""

    kind: str  # "answer" | "error" | "info"
    text: str
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    """Stateful Tell engine for answer-only LLM conversations."""

    def __init__(
        self,
        settings: Settings,
        *,
        cwd: Path | str | None = None,
    ) -> None:
        self.settings = settings
        self.cwd = Path(cwd).resolve() if cwd else Path.cwd()

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
        """Run one answer-only user turn.

        Tell intentionally does not expose tools to the model, so this method
        performs one chat-completion request and yields one final answer.
        """
        self.history.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=self.history,
                temperature=self.settings.temperature,
            )
        except Exception as exc:
            logger.exception("LLM request failed")
            yield AgentEvent("error", f"LLM request failed: {exc}")
            return

        msg = response.choices[0].message
        content = msg.content or ""
        self.history.append({"role": "assistant", "content": content})
        yield AgentEvent("answer", content)

