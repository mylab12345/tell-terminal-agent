"""Command execution backend — cross-platform.

Runs shell commands using the system's default shell (``/bin/sh`` on
Unix, ``cmd.exe`` on Windows) and captures stdout + stderr.  Returns
a structured result so the tool loop can feed the output back to the
model.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"


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
        """Return stdout + stderr, truncated to *limit* chars for the LLM."""
        parts: list[str] = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        text = "\n".join(parts)
        if len(text) > limit:
            text = text[:limit] + f"\n...[truncated {len(text) - limit} chars]"
        return text


def _build_args(command: str, shell: str) -> list[str]:
    """Build the subprocess argument list for the given *shell*."""
    shell_lower = shell.lower().strip()

    if IS_WINDOWS:
        if shell_lower == "powershell":
            return ["powershell.exe", "-NoProfile", "-Command", command]
        # default: cmd
        return ["cmd.exe", "/c", command]

    # Unix-like systems
    if shell_lower == "bash":
        return ["/bin/bash", "-c", command]
    if shell_lower == "zsh":
        return ["/bin/zsh", "-c", command]
    # default: sh (POSIX-portable)
    return ["/bin/sh", "-c", command]


def run_command(
    command: str,
    *,
    cwd: Path | str | None = None,
    timeout: float = 120.0,
    shell: str = "auto",
) -> CommandResult:
    """Run *command* and return a :class:`CommandResult`.

    Args:
        command: The command line to execute.
        cwd: Working directory.  Defaults to the current process directory.
        timeout: Maximum seconds to wait before killing the process.
        shell: Which shell to use.  ``"auto"`` picks the platform default
            (``sh`` on Unix, ``cmd`` on Windows).  Also accepts ``"bash"``,
            ``"zsh"``, ``"powershell"``, ``"cmd"``.
    """
    if shell == "auto":
        shell = "cmd" if IS_WINDOWS else "bash"

    args = _build_args(command, shell)
    logger.debug("Executing %s (shell=%s, cwd=%s)", args, shell, cwd)

    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
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
        logger.warning("Command timed out after %ss: %s", timeout, command)
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
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("Unexpected error running command")
        return CommandResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Failed to execute command: {exc}",
        )
