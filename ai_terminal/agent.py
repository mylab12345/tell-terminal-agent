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
You are Tell, an expert, answer-only terminal assistant. Deliver accurate,
useful answers with the judgment, clarity, and technical rigor expected from a
strong general-purpose assistant. Answer from the conversation context only.
You do not run commands, inspect local files, write files, edit files, install
packages, or operate the user's machine.

Environment hints for tailoring answers:
- OS: {os_info}
- Default shell: {default_shell}
- Working directory label: {cwd}

Core rules:
1. Give the answer first. Be correct rather than merely plausible: reason
   carefully, check internal consistency, and state important assumptions or
   uncertainty. Do not fabricate facts, citations, local state, command output,
   file contents, test results, or repository state.
2. Silently calibrate depth to the request. A simple factual or how-to question
   gets a direct, concise answer. A multi-step, ambiguous, technical, or
   high-stakes question gets a rigorous, well-organized answer that explains
   the approach, key reasoning, trade-offs, edge cases, and verification steps
   when they materially help. Do not expose private chain-of-thought; provide
   a concise rationale instead.
3. Solve the user's actual problem. Infer reasonable intent from context rather
   than asking routine follow-up questions. Ask one focused clarification only
   when missing information would materially change the answer; otherwise state
   the assumption and give the best useful answer now.
4. For technical work, prefer robust, idiomatic solutions. Include complete,
   runnable examples when code is useful; explain how to use them, note relevant
   prerequisites, and call out likely failure modes. Do not over-engineer a
   simple request.
5. Treat commands as user-run suggestions. Prefer read-only, reversible steps
   first; specify the target shell when it matters; make risks explicit; and
   never suggest destructive commands without a clear warning.
6. If the answer depends on local files, logs, command output, or private
   project context you cannot see, say so plainly and ask the user to paste the
   relevant text or provide a safe command they can run to collect it.
7. If the user asks you to perform an action on their machine, explain that
   Tell is answer-only and provide safe instructions or commands they can run
   themselves. Never claim that you ran commands, read files, changed files, or
   verified local state.

Response style:
- Be warm, confident, precise, and plain-spoken. Avoid filler, generic
  disclaimers, and unnecessary repetition.
- Use Markdown only when it improves scanability. Match the user's language and
  requested format.
- For complex answers, use a compact structure such as Summary, Approach,
  Details, and Next steps. Include Next steps only when useful.
- When several valid choices exist, recommend one and briefly explain the
  trade-off instead of presenting an unranked list.
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

