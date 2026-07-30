"""Command execution backend for the AI terminal agent.

Runs shell commands on Windows using ``cmd.exe`` (the default shell for this
project) with a timeout and captures stdout + stderr.  Returns a structured
result so the agent loop can feed the output back to the model.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    """Outcome of running a single command."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def combined_output(self, limit: int = 4000) -> str:
        """Return stdout+stderr, truncated to *limit* chars for the LLM."""
        parts: list[str] = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        text = "\n".join(parts)
        if len(text) > limit:
            text = text[:limit] + f"\n...[truncated {len(text) - limit} chars]"
        return text


def run_command(
    command: str,
    *,
    cwd: Path | str | None = None,
    timeout: float = 120.0,
    shell: str = "cmd",
) -> CommandResult:
    """Run *command* and return a :class:`CommandResult`.

    Args:
        command: The command line to execute.
        cwd: Working directory. Defaults to the current process directory.
        timeout: Maximum seconds to wait before killing the process.
        shell: ``"cmd"`` uses ``cmd.exe /c``; ``"powershell"`` uses
            ``powershell.exe -NoProfile -Command``.
    """
    if shell == "powershell":
        args = ["powershell.exe", "-NoProfile", "-Command", command]
    else:
        args = ["cmd.exe", "/c", command]

    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding=None,
            errors="backslashreplace",
            timeout=timeout,
        )
        return CommandResult(
            command=command,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s and was killed.",
            timed_out=True,
        )
    except FileNotFoundError as exc:
        return CommandResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Shell not found: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive
        return CommandResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Failed to execute command: {exc}",
        )