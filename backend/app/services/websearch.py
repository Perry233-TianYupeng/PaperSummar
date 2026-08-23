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


def snippets_to_text(results: list[SearchResult], limit: int = 5) -> str:
    """将搜索结果序列化为 LLM 可读的文本块。"""
    lines: list[str] = []
    for r in results[:limit]:
        lines.append(f"- {r.title}\n  {r.url}\n  {r.snippet}")
    return "\n".join(lines)
