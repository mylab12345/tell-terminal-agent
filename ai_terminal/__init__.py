"""Tell — a cross-platform answer-only terminal assistant.

A dependency-light assistant that uses an OpenAI-compatible chat model to
answer terminal questions on any platform (Linux, macOS, Windows). Tell's
runtime does not execute commands or modify local files.
"""

from __future__ import annotations

from .agent import Agent, AgentEvent
from .config import Settings, load_settings
from .executor import CommandResult, run_command
from .safety import SafetyVerdict, assess

__all__ = [
    "Agent",
    "AgentEvent",
    "CommandResult",
    "SafetyVerdict",
    "Settings",
    "assess",
    "load_settings",
    "run_command",
]

__version__ = "0.2.0"
