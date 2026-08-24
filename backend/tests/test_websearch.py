"""搜索层测试：create_searcher 选择逻辑、TavilySearcher 请求与解析。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.models import Settings  # noqa: E402
from app.services.websearch import (  # noqa: E402
    DeepSeekWebSearcher,
    DuckDuckGoSearcher,
    TavilySearcher,
    _anthropic_endpoint,
    create_searcher,
)


class TestCreateSearcher:
    def test_default_is_duckduckgo(self) -> None:
        assert isinstance(create_searcher(Settings()), DuckDuckGoSearcher)

    def test_duckduckgo_explicit(self) -> None:
        s = Settings(search_provider="duckduckgo", search_api_key="tvly-test")
        assert isinstance(create_searcher(s), DuckDuckGoSearcher)

    def test_tavily_with_key(self) -> None:
        s = Settings(search_provider="tavily", search_api_key="tvly-test-key")
        assert isinstance(create_searcher(s), TavilySearcher)

    def test_tavily_without_key_raises(self) -> None:
        s = Settings(search_provider="tavily", search_api_key="")
        with pytest.raises(ValueError, match="Tavily"):
            create_searcher(s)

    def test_deepseek_with_deepseek_llm(self) -> None:
        s = Settings(
            search_provider="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
        )
        assert isinstance(create_searcher(s), DeepSeekWebSearcher)

    def test_deepseek_without_deepseek_llm_raises(self) -> None:
        s = Settings(
            search_provider="deepseek",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
        )
        with pytest.raises(ValueError, match="DeepSeek"):
            create_searcher(s)


class TestAnthropicEndpoint:
    def test_derives_from_v1_base_url(self) -> None:
        assert (
            _anthropic_endpoint("https://api.deepseek.com/v1")
            == "https://api.deepseek.com/anthropic/v1/messages"
        )

    def test_derives_from_bare_base_url(self) -> None:
        assert (
            _anthropic_endpoint("https://api.deepseek.com")
            == "https://api.deepseek.com/anthropic/v1/messages"
        )


class TestDeepSeekWebSearcher:
    def test_missing_key_raises(self) -> None:
        with pytest.raises(ValueError, match="DeepSeek"):
            DeepSeekWebSearcher("", "deepseek-v4-flash", "https://api.deepseek.com/v1")

    def test_search_parses_text_and_sources(self, monkeypatch) -> None:
        import httpx

        class FakeResp:
            status_code = 200

            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return {
                    "content": [
                        {"type": "text", "text": "Attention 论文 2017 年发表在 NeurIPS。"},
                        {
                            "type": "source",
                            "source": {
                                "citations": [
                                    {"url": "https://arxiv.org/abs/1706.03762"},
                                    {"url": "https://example.com/paper"},
                                ]
                            },
                        },
                    ]
                }

        def fake_post(url, json=None, headers=None, timeout=None):
            assert "anthropic/v1/messages" in url
            tools = json["tools"]
            assert tools == [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}]
            assert headers["Authorization"] == "Bearer sk-deepseek"
            return FakeResp()

        monkeypatch.setattr(httpx, "post", fake_post)
        searcher = DeepSeekWebSearcher("sk-deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1")
        results = searcher.search("Attention Is All You Need")
        assert len(results) == 1
        assert "NeurIPS" in results[0].snippet
        assert "arxiv.org/abs/1706.03762" in results[0].snippet

    def test_search_swallows_errors(self, monkeypatch) -> None:
        import httpx

        def fake_post(url, json=None, headers=None, timeout=None):
            raise httpx.ConnectError("network down")

        monkeypatch.setattr(httpx, "post", fake_post)
        searcher = DeepSeekWebSearcher("sk-deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1")
        assert searcher.search("query") == []


class TestTavilySearcher:
    def test_missing_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Tavily"):
            TavilySearcher("")

    def test_search_parses_results(self, monkeypatch) -> None:
        import httpx

        class FakeResp:
            status_code = 200

            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return {
                    "results": [
                        {
                            "title": "Attention Is All You Need",
                            "url": "https://arxiv.org/abs/1706.03762",
                            "content": "We propose the Transformer, a new architecture...",
                        },
                        {"title": "No URL Here", "content": "should be skipped"},
                    ]
                }

        def fake_post(url, json=None, headers=None, timeout=None):
            assert url == "https://api.tavily.com/search"
            assert headers == {"Authorization": "Bearer tvly-test"}
            assert json["search_depth"] == "advanced"
            return FakeResp()

        monkeypatch.setattr(httpx, "post", fake_post)
        searcher = TavilySearcher("tvly-test")
        results = searcher.search("Attention Is All You Need")
        assert len(results) == 1
        assert results[0].title == "Attention Is All You Need"
        assert results[0].url == "https://arxiv.org/abs/1706.03762"
        assert "Transformer" in results[0].snippet

    def test_search_swallows_errors(self, monkeypatch) -> None:
        import httpx

        def fake_post(url, json=None, headers=None, timeout=None):
            raise httpx.ConnectError("network down")

        monkeypatch.setattr(httpx, "post", fake_post)
        searcher = TavilySearcher("tvly-test")
        assert searcher.search("query") == []
