"""Safety checks for shell commands proposed by Tell.

The goal is not to be a perfect sandbox (that is impossible without a real
sandbox) but to give the user a clear, last-chance confirmation before
running commands that look destructive or irreversible.

Covers both **Windows** and **Unix/macOS** patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Dangerous patterns
# ---------------------------------------------------------------------------
# Patterns that are almost always dangerous.  We match case-insensitively
# against the whole command string.

_DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ---- Unix / macOS ----
    (re.compile(r"\brm\s+-[a-z]*r", re.I), "recursive delete (rm -r)"),
    (re.compile(r"\brm\s+-[a-z]*f", re.I), "force delete (rm -f)"),
    (re.compile(r"\brm\s+/\s", re.I), "delete root directory"),
    (re.compile(r"\bmkfs\b", re.I), "format filesystem (mkfs)"),
    (re.compile(r"\bdd\s+.*of=/dev/", re.I), "raw disk write (dd)"),
    (re.compile(r"\bchmod\s+-[a-z]*R\s+777", re.I), "recursive chmod 777"),
    (re.compile(r"\bchown\s+-[a-z]*R", re.I), "recursive chown"),
    (re.compile(r">\s*/dev/sd[a-z]", re.I), "overwrite block device"),
    (re.compile(r"\bshutdown\b", re.I), "shutdown/reboot"),
    (re.compile(r"\breboot\b", re.I), "reboot"),
    (re.compile(r"\binit\s+[0-6]\b", re.I), "change runlevel"),
    (re.compile(r"\bsystemctl\s+(poweroff|reboot|halt)", re.I), "system power control"),
    (re.compile(r"\bcurl\b.*\|\s*(bash|sh|zsh|python)", re.I), "pipe download to shell"),
    (re.compile(r"\bwget\b.*\|\s*(bash|sh|zsh|python)", re.I), "pipe download to shell"),
    (re.compile(r":[(][)]\s*[{]\s*:|:&\s*[}]", re.I), "fork bomb"),
    (re.compile(r"\bkillall\b", re.I), "kill all processes"),
    (re.compile(r"\bpkill\s+-9", re.I), "force-kill processes"),
    (re.compile(r"\biptables\s+-F", re.I), "flush firewall rules"),
    (re.compile(r"\bufw\s+disable", re.I), "disable firewall"),
    (re.compile(r"\bpasswd\b", re.I), "change password"),
    (re.compile(r"\busermod\b", re.I), "modify user account"),
    (re.compile(r"\buserdel\b", re.I), "delete user account"),
    (re.compile(r"\bvisudo\b", re.I), "edit sudoers"),
    (re.compile(r"\bcrontab\s+-r\b", re.I), "remove all cron jobs"),

    # ---- Windows ----
    (re.compile(r"\bformat\b", re.I), "format drive"),
    (re.compile(r"\bdiskpart\b", re.I), "disk partitioning"),
    (re.compile(r"\bdel\s+/[a-z]*s", re.I), "recursive delete (del /s)"),
    (re.compile(r"\brmdir\s+/[a-z]*s", re.I), "recursive rmdir"),
    (re.compile(r"\brd\s+/[a-z]*s", re.I), "recursive rd"),
    (re.compile(r"Remove-Item.*-Recurse", re.I), "recursive Remove-Item"),
    (re.compile(r"Remove-Item.*-Force", re.I), "force Remove-Item"),
    (re.compile(r"\breg\s+add\b", re.I), "registry add"),
    (re.compile(r"\breg\s+delete\b", re.I), "registry delete"),
    (re.compile(r"\breg\s+import\b", re.I), "registry import"),
    (re.compile(r"\brestart-computer\b", re.I), "restart computer"),
    (re.compile(r"\bstop-computer\b", re.I), "stop computer"),
    (re.compile(r"\btaskkill\s+/[a-z]*f", re.I), "force-kill process"),
    (re.compile(r"\bStop-Process.*-Force", re.I), "force stop process"),
    (re.compile(r"\btakeown\b", re.I), "take ownership"),
    (re.compile(r"\bicacls\b", re.I), "change ACLs"),
    (re.compile(r"ExecutionPolicy\s+Bypass", re.I), "bypass execution policy"),

    # ---- Cross-platform supply-chain risk ----
    (re.compile(r"pip\s+install\s+https?://", re.I), "pip install from URL"),
    (re.compile(r"npm\s+install\s+https?://", re.I), "npm install from URL"),
]


@dataclass(frozen=True)
class SafetyVerdict:
    """Result of a safety check on a proposed command."""

    is_dangerous: bool
    reason: str

    @classmethod
    def safe(cls) -> SafetyVerdict:
        return cls(is_dangerous=False, reason="")

    @classmethod
    def dangerous(cls, reason: str) -> SafetyVerdict:
        return cls(is_dangerous=True, reason=reason)


def assess(command: str) -> SafetyVerdict:
    """Return a :class:`SafetyVerdict` for *command*.

    Only returns ``dangerous`` when a known risky pattern matches.  Anything
    not matched is treated as safe (the user is still shown the command
    before it runs in interactive mode).
    """
    if not command or not command.strip():
        return SafetyVerdict.safe()

    for pattern, description in _DANGEROUS_PATTERNS:
        if pattern.search(command):
            return SafetyVerdict.dangerous(
                f"Matched risky pattern: {description}"
            )

    return SafetyVerdict.safe()
