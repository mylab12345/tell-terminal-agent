"""AI Terminal Agent — a cross-platform AI coding agent.

A dependency-light agent that uses an OpenAI-compatible chat model
to plan and run shell commands, read/write files, and help with
coding tasks on any platform (Linux, macOS, Windows).
"""

from __future__ import annotations

from .agent import Agent, AgentEvent
from .config import Settings, load_settings
from .executor import CommandResult, run_command
from .safety import SafetyVerdict, assess

__all__ = [
    "Agent",
    "AgentEvent",
    "Settings",
    "load_settings",
    "CommandResult",
    "run_command",
    "SafetyVerdict",
    "assess",
]

__version__ = "0.2.0"
