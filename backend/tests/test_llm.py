"""LLM 客户端错误处理测试：401/429 应转换为友好中文提示。"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import openai  # noqa: E402
from app.services import llm as llm_module  # noqa: E402


def _http_resp(status: int) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "https://example.com"))


class _FakeCompletions:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, **kwargs):
        raise self._exc


class _FakeClient:
    """模拟 OpenAI 客户端，create 抛指定异常。"""

    def __init__(self, exc: Exception) -> None:
        self.chat = _FakeChat(exc)


class _FakeChat:
    def __init__(self, exc: Exception) -> None:
        self.completions = _FakeCompletions(exc)


def _make_client(exc: Exception, monkeypatch) -> llm_module.LLMClient:
    def fake_openai(**kwargs):
        return _FakeClient(exc)

    monkeypatch.setattr(openai, "OpenAI", fake_openai)
    return llm_module.LLMClient("sk-test", "https://example.com/v1", "test-model")


def test_authentication_error_friendly_message(monkeypatch) -> None:
    exc = openai.AuthenticationError(
        "401 invalid key",
        response=_http_resp(401),
        body={"error": {"message": "invalid"}},
    )
    client = _make_client(exc, monkeypatch)
    with pytest.raises(RuntimeError) as ei:
        client.chat_json("prompt")
    assert "API Key" in str(ei.value)
    assert "401" in str(ei.value)


def test_rate_limit_error_friendly_message(monkeypatch) -> None:
    exc = openai.RateLimitError(
        "429 too many",
        response=_http_resp(429),
        body={"error": {"message": "rate"}},
    )
    client = _make_client(exc, monkeypatch)
    with pytest.raises(RuntimeError) as ei:
        client.chat_json("prompt")
    assert "限流" in str(ei.value) or "429" in str(ei.value)


def test_no_api_key_raises() -> None:
    with pytest.raises(ValueError, match="API Key"):
        llm_module.LLMClient("", "https://example.com/v1", "m")
