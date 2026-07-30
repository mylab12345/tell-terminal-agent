"""Tests for the config module."""

from __future__ import annotations

import os
from unittest.mock import patch

from ai_terminal.config import Settings, _as_float, _as_int, load_settings


class TestSettings:
    def test_is_configured_with_real_key(self):
        s = Settings(
            api_key="gsk_abc123",
            model="test",
            base_url=None,
            temperature=0.2,
            max_auto_steps=5,
            provider="groq",
        )
        assert s.is_configured

    def test_is_not_configured_empty(self):
        s = Settings(
            api_key="",
            model="test",
            base_url=None,
            temperature=0.2,
            max_auto_steps=5,
            provider="groq",
        )
        assert not s.is_configured

    def test_is_not_configured_placeholder(self):
        s = Settings(
            api_key="your-key",
            model="test",
            base_url=None,
            temperature=0.2,
            max_auto_steps=5,
            provider="groq",
        )
        assert not s.is_configured


class TestHelpers:
    def test_as_float_valid(self):
        assert _as_float("0.5", 0.2) == 0.5

    def test_as_float_invalid(self):
        assert _as_float("not-a-number", 0.2) == 0.2

    def test_as_float_none(self):
        assert _as_float(None, 0.7) == 0.7

    def test_as_int_valid(self):
        assert _as_int("10", 5) == 10

    def test_as_int_invalid(self):
        assert _as_int("abc", 5) == 5


class TestLoadSettings:
    @patch.dict(os.environ, {
        "AI_PROVIDER": "groq",
        "GROQ_API_KEY": "test-key-123",
        "AI_MODEL": "test-model",
    }, clear=False)
    def test_loads_from_env(self, tmp_path):
        s = load_settings(env_path=tmp_path / "nonexistent.env")
        assert s.api_key == "test-key-123"
        assert s.model == "test-model"
        assert s.provider == "groq"

    @patch.dict(os.environ, {
        "AI_PROVIDER": "unknown_provider_xyz",
    }, clear=False)
    def test_unknown_provider_falls_back(self, tmp_path):
        s = load_settings(env_path=tmp_path / "nonexistent.env")
        assert s.provider == "groq"
