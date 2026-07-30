"""Configuration loading for the AI terminal agent.

Reads settings from environment variables and a local ``.env`` file so the
agent can be configured without editing source code.  Supports several
free-tier OpenAI-compatible providers (Groq, Google Gemini, OpenRouter,
Cerebras, SambaNova) via a single ``AI_PROVIDER`` switch.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional at runtime
    def load_dotenv(*_args, **_kwargs):  # type: ignore[misc]
        return False


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Known free-tier OpenAI-compatible providers.  Each preset supplies a
# base URL, a default model, and the name of the env var that holds the
# API key.  All of these expose an OpenAI-compatible /chat/completions
# endpoint so the same `openai` client works for every provider.
PROVIDERS: dict[str, dict[str, str]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "label": "Groq (free tier — https://console.groq.com/keys)",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-1.5-flash",
        "key_env": "GEMINI_API_KEY",
        "label": "Google Gemini (free — https://aistudio.google.com/apikey)",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_env": "OPENROUTER_API_KEY",
        "label": "OpenRouter (free models — https://openrouter.ai/keys)",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "model": "llama-3.1-8b-instant",
        "key_env": "CEREBRAS_API_KEY",
        "label": "Cerebras (free — https://cloud.cerebras.ai)",
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "model": "Meta-Llama-3.1-70B-Instruct",
        "key_env": "SAMBANOVA_API_KEY",
        "label": "SambaNova (free — https://cloud.sambanova.ai)",
    },
    "openai": {
        "base_url": "",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
        "label": "OpenAI (paid — https://platform.openai.com/api-keys)",
    },
}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the agent."""

    api_key: str
    model: str
    base_url: str | None
    temperature: float
    max_auto_steps: int
    provider: str

    @property
    def is_configured(self) -> bool:
        """Return True when an API key is present and non-placeholder."""
        return bool(self.api_key) and not self.api_key.startswith("sk-your-key") \
            and not self.api_key.lower() in ("your-key", "placeholder")


def _as_float(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_settings(env_path: Path | str | None = None) -> Settings:
    """Load settings from ``.env`` and the process environment.

    Args:
        env_path: Optional path to a ``.env`` file. Defaults to
            ``<project_root>/.env``.
    """
    if env_path is None:
        env_path = PROJECT_ROOT / ".env"
    load_dotenv(str(env_path))

    provider = os.getenv("AI_PROVIDER", "groq").strip().lower() or "groq"
    preset = PROVIDERS.get(provider, PROVIDERS["groq"])

    # Resolve the API key: prefer the provider-specific env var, then fall
    # back to OPENAI_API_KEY (useful when switching providers quickly).
    key_env = preset["key_env"]
    api_key = (os.getenv(key_env) or os.getenv("OPENAI_API_KEY") or "").strip()

    # Allow explicit overrides via env vars; otherwise use the preset.
    model = (os.getenv("AI_MODEL") or preset["model"]).strip() or preset["model"]
    base_url = (os.getenv("OPENAI_BASE_URL") or preset["base_url"]).strip() or None

    return Settings(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=_as_float(os.getenv("AI_TEMPERATURE"), 0.2),
        max_auto_steps=_as_int(os.getenv("MAX_AUTO_STEPS"), 5),
        provider=provider,
    )
