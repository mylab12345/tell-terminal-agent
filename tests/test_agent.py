"""Tests for the answer-only Tell loop."""

from __future__ import annotations

from ai_terminal.agent import Agent, SYSTEM_PROMPT
from ai_terminal.config import Settings


class _FakeMessage:
    content = "Tell answer"


class _FakeChoice:
    def __init__(self) -> None:
        self.message = _FakeMessage()


class _FakeResponse:
    def __init__(self) -> None:
        self.choices = [_FakeChoice()]


class _FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _FakeResponse()


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self) -> None:
        self.chat = _FakeChat()


def _settings() -> Settings:
    return Settings(
        api_key="test-key",
        model="test-model",
        base_url=None,
        temperature=0.2,
        max_auto_steps=5,
        provider="test",
    )


def test_agent_does_not_expose_tools_to_model(monkeypatch):
    fake_client = _FakeClient()

    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake_client)

    agent = Agent(_settings())
    events = list(agent.run("hello"))

    assert len(events) == 1
    assert events[0].kind == "answer"
    assert events[0].text == "Tell answer"

    request = fake_client.chat.completions.kwargs
    assert request is not None
    assert request["model"] == "test-model"
    assert request["temperature"] == 0.2
    assert "tools" not in request
    assert "tool_choice" not in request


def test_system_prompt_adapts_depth_without_exposing_reasoning():
    prompt = SYSTEM_PROMPT.format(
        os_info="TestOS 1.0 (test)",
        default_shell="bash",
        cwd="/tmp/project",
    )

    assert "Silently calibrate depth to the request" in prompt
    assert "simple factual or how-to question" in prompt
    assert "multi-step, ambiguous, technical, or high-stakes question" in prompt
    assert "Do not expose private chain-of-thought" in prompt
    assert "Give the answer first" in prompt
