"""DuckDuckGo 网页搜索封装（兜底搜索源）。

使用 ``ddgs`` 库（duckduckgo_search 的新包名）。搜索失败不致命——
仅提供网页证据片段给 LLM 参考；arXiv 元数据已能支撑大部分字段。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..utils.logging_setup import get_logger

_logger = get_logger()


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class DuckDuckGoSearcher:
    """带重试与退避的 DuckDuckGo 搜索封装。"""

    def __init__(self, max_results: int = 5, max_retries: int = 2, timeout: int = 15) -> None:
        self.max_results = max_results
        self.max_retries = max_retries
        self.timeout = timeout

    def search(self, query: str) -> list[SearchResult]:
        """返回搜索结果；任何异常时返回空列表（不抛出）。"""
        query = (query or "").strip()
        if not query:
            return []
        for attempt in range(self.max_retries + 1):
            try:
                raw = self._do_search(query)
                return [self._clean(r) for r in raw if isinstance(r, dict) and r.get("href")]
            except Exception as exc:  # noqa: BLE001 - 搜索兜底，失败降级
                _logger.warning("DuckDuckGo 搜索第 %s 次失败：%s", attempt + 1, exc)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
        return []

    def _do_search(self, query: str) -> list[Any]:
        from ddgs import DDGS  # 惰性导入，避免未安装时阻断其余模块

        with DDGS(timeout=self.timeout) as ddgs:
            results = ddgs.text(query, max_results=self.max_results)
            return results if isinstance(results, list) else []

    def _clean(self, raw: dict[str, Any]) -> SearchResult:
        return SearchResult(
            title=str(raw.get("title") or "").strip(),
            url=str(raw.get("href") or "").strip(),
            snippet=str(raw.get("body") or "").strip(),
        )


class TavilySearcher:
    """Tavily 搜索（高质量，专为 LLM 检索设计，需 API key）。

    返回的 content 是网页正文提取的完整摘要，信息量远大于搜索引擎的
    一两行 snippet，能显著改善「期刊/会议、内容、创新点」等字段的补全质量。
    """

    def __init__(self, api_key: str, max_results: int = 6, timeout: float = 20.0) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("未配置 Tavily API Key，请先在「个人设置」中填写")
        self._api_key = api_key.strip()
        self.max_results = max_results
        self.timeout = timeout

    def search(self, query: str) -> list[SearchResult]:
        """返回搜索结果；任何异常时返回空列表（不抛出，交由上层降级）。"""
        query = (query or "").strip()
        if not query:
            return []
        try:
            raw = self._do_search(query)
            return [self._clean(r) for r in raw if isinstance(r, dict) and r.get("url")]
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Tavily 搜索失败：%s", exc)
            return []

    def _do_search(self, query: str) -> list[Any]:
        import httpx  # 惰性导入

        payload = {
            "query": query,
            "search_depth": "advanced",  # 更深入的抓取，内容更完整
            "max_results": self.max_results,
            "include_answer": True,  # 附带 LLM 可直接使用的回答
        }
        resp = httpx.post(
            "https://api.tavily.com/search",
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", []) if isinstance(data, dict) else []

    def _clean(self, raw: dict[str, Any]) -> SearchResult:
        return SearchResult(
            title=str(raw.get("title") or "").strip(),
            url=str(raw.get("url") or "").strip(),
            snippet=str(raw.get("content") or "").strip(),
        )


class DeepSeekWebSearcher:
    """DeepSeek 内置联网搜索（web_search_20250305，走 Anthropic 兼容端点）。

    复用用户的 DeepSeek API key，按 token 计费（无单独检索费）。由 DeepSeek
    服务端完成「搜索 → 抓取 → 解密 → 生成带引用的回答」，我们把回答文本作为
    搜索证据交给后续 LLM 做结构化提取。
    """

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 60.0) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("未配置 DeepSeek API Key")
        self._api_key = api_key.strip()
        self.model = model
        self._endpoint = _anthropic_endpoint(base_url)
        self.timeout = timeout

    def search(self, query: str) -> list[SearchResult]:
        """返回搜索结果；任何异常时返回空列表（不抛出，交由上层降级）。"""
        query = (query or "").strip()
        if not query:
            return []
        try:
            text, sources = self._do_search(query)
            if not text:
                return []
            snippet = text
            if sources:
                snippet += "\n\n来源：\n" + "\n".join(f"- {u}" for u in sources[:10])
            return [SearchResult(title="DeepSeek 联网搜索", url="", snippet=snippet)]
        except Exception as exc:  # noqa: BLE001
            _logger.warning("DeepSeek 联网搜索失败：%s", exc)
            return []

    def _do_search(self, query: str) -> tuple[str, list[str]]:
        import httpx  # 惰性导入

        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
            "messages": [{"role": "user", "content": query}],
        }
        resp = httpx.post(
            self._endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        texts: list[str] = []
        sources: list[str] = []
        content = data.get("content") if isinstance(data, dict) else None
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text" and block.get("text"):
                    texts.append(str(block["text"]))
                elif btype == "source":
                    for cite in (block.get("source") or {}).get("citations") or []:
                        if isinstance(cite, dict) and cite.get("url"):
                            sources.append(str(cite["url"]))
        return "\n".join(texts).strip(), sources


def is_deepseek_base_url(base_url: str) -> bool:
    """判断 LLM 服务是否为 DeepSeek（其 base_url 含 deepseek.com）。"""
    return "deepseek.com" in (base_url or "").lower()


def _anthropic_endpoint(base_url: str) -> str:
    """从 OpenAI 兼容 base_url 推导 DeepSeek 的 Anthropic 兼容端点。

    https://api.deepseek.com/v1  →  https://api.deepseek.com/anthropic/v1/messages
    https://api.deepseek.com     →  https://api.deepseek.com/anthropic/v1/messages
    """
    base = (base_url or "").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[: -3]
    return f"{base}/anthropic/v1/messages"


def create_searcher(settings) -> DuckDuckGoSearcher | TavilySearcher | DeepSeekWebSearcher:
    """按用户选择的搜索方式创建搜索器。

    - duckduckgo：完全免费兜底
    - tavily：需配置 Tavily API Key（免费额度约 1000 次/月）
    - deepseek：需 LLM 服务为 DeepSeek 且配置了 API Key（按 token 计费）
    配置不满足时抛出 ValueError，由上层给出友好提示。
    """
    if settings.search_provider == "tavily":
        if not settings.search_api_key.strip():
            raise ValueError("已选择 Tavily 搜索，但尚未配置 Tavily API Key，请到「个人设置」填写")
        return TavilySearcher(settings.search_api_key)
    if settings.search_provider == "deepseek":
        if not is_deepseek_base_url(settings.base_url) or not settings.api_key.strip():
            raise ValueError(
                "已选择 DeepSeek 联网搜索，但 LLM 服务不是 DeepSeek 或未配置 API Key，"
                "请到「个人设置」将 Base URL 设为 api.deepseek.com 并填写 API Key"
            )
        return DeepSeekWebSearcher(settings.api_key, settings.model, settings.base_url)
    return DuckDuckGoSearcher()


def snippets_to_text(results: list[SearchResult], limit: int = 5) -> str:
    """将搜索结果序列化为 LLM 可读的文本块。"""
    lines: list[str] = []
    for r in results[:limit]:
        lines.append(f"- {r.title}\n  {r.url}\n  {r.snippet}")
    return "\n".join(lines)
