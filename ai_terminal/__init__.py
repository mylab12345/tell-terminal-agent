"""AITA - AI Terminal Agent for Windows 11.

A small, dependency-light agent that uses an OpenAI-compatible chat model
to plan and run shell commands on the user's machine, with safety checks
and interactive confirmation.
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

__version__ = "0.1.0"