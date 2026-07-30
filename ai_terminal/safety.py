"""Safety checks for shell commands proposed by the AI agent.

The goal is not to be a perfect sandbox (that is impossible without a real
sandbox) but to give the user a clear, last-chance confirmation before
running commands that look destructive or irreversible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Patterns that are almost always dangerous on Windows.  We match
# case-insensitively and against the whole command string.
_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    # Formatting / wiping drives
    re.compile(r"\bformat\b", re.IGNORECASE),
    re.compile(r"\bdiskpart\b", re.IGNORECASE),
    # Deleting large trees or whole drives
    re.compile(r"\bdel\s+/[a-z]*s", re.IGNORECASE),
    re.compile(r"\brmdir\s+/[a-z]*s", re.IGNORECASE),
    re.compile(r"\brd\s+/[a-z]*s", re.IGNORECASE),
    re.compile(r"\brm\s+-[a-z]*r", re.IGNORECASE),
    re.compile(r"\brm\s+-[a-z]*f", re.IGNORECASE),
    re.compile(r"Remove-Item.*-Recurse", re.IGNORECASE),
    re.compile(r"Remove-Item.*-Force", re.IGNORECASE),
    # Registry edits
    re.compile(r"\breg\s+add\b", re.IGNORECASE),
    re.compile(r"\breg\s+delete\b", re.IGNORECASE),
    re.compile(r"\breg\s+import\b", re.IGNORECASE),
    # Shutdown / reboot
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\brestart-computer\b", re.IGNORECASE),
    re.compile(r"\bstop-computer\b", re.IGNORECASE),
    # Network exfiltration-ish
    re.compile(r"\bcurl\b.*\|\s*(bash|sh|pwsh|powershell)", re.IGNORECASE),
    re.compile(r"\biwr\b.*\|\s*(bash|sh|pwsh|powershell)", re.IGNORECASE),
    re.compile(r"Invoke-WebRequest.*-OutFile\s+\\\\", re.IGNORECASE),
    # Force-killing processes broadly
    re.compile(r"\btaskkill\s+/[a-z]*f", re.IGNORECASE),
    re.compile(r"\bStop-Process.*-Force", re.IGNORECASE),
    # Filesystem-wide ownership / permission changes
    re.compile(r"\btakeown\b", re.IGNORECASE),
    re.compile(r"\bicacls\b", re.IGNORECASE),
    # PowerShell execution policy bypass + download
    re.compile(r"ExecutionPolicy\s+Bypass", re.IGNORECASE),
    # Pip install from arbitrary URLs (supply-chain risk)
    re.compile(r"pip\s+install\s+https?://", re.IGNORECASE),
    # Wiping the user profile / home
    re.compile(r"del\s+/[a-z]*q?\s+%USERPROFILE%", re.IGNORECASE),
    re.compile(r"rm\s+-[a-z]*rf?\s+~/", re.IGNORECASE),
]


@dataclass(frozen=True)
class SafetyVerdict:
    """Result of a safety check on a proposed command."""

    is_dangerous: bool
    reason: str

    @classmethod
    def safe(cls) -> "SafetyVerdict":
        return cls(is_dangerous=False, reason="")

    @classmethod
    def dangerous(cls, reason: str) -> "SafetyVerdict":
        return cls(is_dangerous=True, reason=reason)


def assess(command: str) -> SafetyVerdict:
    """Return a :class:`SafetyVerdict` for *command*.

    Only returns ``dangerous`` when a known risky pattern matches.  Anything
    not matched is treated as safe (the user is still shown the command
    before it runs in interactive mode).
    """
    if not command or not command.strip():
        return SafetyVerdict.safe()

    for pattern in _DANGEROUS_PATTERNS:
        match = pattern.search(command)
        if match:
            return SafetyVerdict.dangerous(
                f"Matched risky pattern: /{pattern.pattern}/"
            )
    return SafetyVerdict.safe()