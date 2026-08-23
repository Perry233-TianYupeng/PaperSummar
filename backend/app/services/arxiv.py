"""arXiv API 客户端。

- 按 ID 查询：``id_list=1706.03762``
- 按标题搜索：``search_query=ti:"..."`` 取 top1
- 解析 Atom XML（含命名空间），显式识别 arXiv 的"伪装错误"
  （HTTP 200 但 ``<title>Error</title>`` 或 body 含 ``Rate exceeded.``）。
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..utils.logging_setup import get_logger

ARXIV_API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "PaperSummar/0.1 (personal paper manager; +https://github.com/PaperSummar)"
MIN_REQUEST_INTERVAL = 3.0  # arXiv 官方建议请求间隔 ≥3s

_logger = get_logger()


@dataclass
class ArxivResult:
    """从 arXiv 提取到的论文元数据。"""

    title: str = ""
    authors: str = ""
    published: str = ""
    journal_ref: str = ""
    summary: str = ""
    doi: str = ""
    links: list[str] = field(default_factory=list)
    arxiv_id: str = ""

    def to_llm_context(self) -> dict[str, Any]:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "published": self.published,
            "journal_ref": self.journal_ref,
            "abstract": self.summary,
        }


class ArxivClient:
    """带限速与容错的 arXiv 查询客户端。"""

    def __init__(self, timeout: float = 20.0, proxy: str | None = None) -> None:
        self._timeout = timeout
        self._last_request = 0.0
        self._http = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            proxy=proxy or None,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    # ---------- 对外查询 ----------

    def query_by_id(self, arxiv_id: str) -> ArxivResult | None:
        """按 arxiv ID 查询，未命中返回 None。"""
        arxiv_id = arxiv_id.strip()
        if not arxiv_id:
            return None
        params = {"id_list": arxiv_id, "max_results": 1}
        return self._fetch(params)

    def query_by_title(self, title: str) -> ArxivResult | None:
        """按标题模糊搜索，取 top1；未命中返回 None。"""
        title = title.strip().strip('"')
        if not title:
            return None
        params = {"search_query": f'ti:"{title}"', "max_results": 1, "sortBy": "relevance"}
        return self._fetch(params)

    # ---------- 内部 ----------

    def _throttle(self) -> None:
        """确保两次请求间隔 ≥ MIN_REQUEST_INTERVAL，遵守 arXiv 限速要求。"""
        elapsed = time.time() - self._last_request
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request = time.time()

    def _fetch(self, params: dict[str, Any]) -> ArxivResult | None:
        self._throttle()
        try:
            resp = self._http.get(ARXIV_API_URL, params=params)
        except httpx.HTTPError as exc:
            _logger.warning("arXiv 请求失败：%s", exc)
            raise RuntimeError(f"arXiv 网络请求失败：{exc}") from exc

        if resp.status_code != 200:
            _logger.warning("arXiv 返回状态码 %s", resp.status_code)
            raise RuntimeError(f"arXiv 返回状态码 {resp.status_code}")

        body = resp.text
        # 限速 / 伪装错误识别
        if "Rate exceeded." in body or "<title>Error</title>" in body:
            _logger.warning("arXiv 返回伪装错误/限速，视为未命中：%s", body[:200])
            return None

        parsed = _parse_atom(body)
        if parsed is None or not parsed.title:
            return None
        return parsed


def _parse_atom(xml_text: str) -> ArxivResult | None:
    """解析 arXiv Atom XML，返回首个 entry 的元数据。"""
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        _logger.warning("arXiv 返回内容不是合法 XML")
        return None

    entry = root.find("a:entry", ns)
    if entry is None:
        return None

    def text(tag: str) -> str:
        node = entry.find(tag, ns)
        return (node.text or "").strip() if node is not None and node.text else ""

    authors = [
        (n.text or "").strip()
        for n in entry.findall("a:author/a:name", ns)
        if n.text
    ]
    links = [
        (ln.attrib.get("href") or "")
        for ln in entry.findall("a:link", ns)
        if ln.attrib.get("href")
    ]

    arxiv_id = text("a:id")
    if arxiv_id.startswith("http://arxiv.org/abs/"):
        arxiv_id = arxiv_id.rsplit("/", 1)[-1]

    return ArxivResult(
        title=text("a:title"),
        authors=", ".join(authors),
        published=text("a:published"),
        journal_ref=text("arxiv:journal_ref"),
        summary=text("a:summary"),
        doi=text("arxiv:doi"),
        links=links,
        arxiv_id=arxiv_id,
    )


def extract_repo_urls(*texts: str) -> str | None:
    """从文本片段中提取第一个 GitHub / GitLab 仓库链接；无则返回 None。"""
    pattern = re.compile(
        r"https?://(?:www\.)?(?:github\.com|gitlab\.com)/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
    )
    for t in texts:
        if not t:
            continue
        m = pattern.search(t)
        if m:
            return m.group(0).rstrip("/")
    return None
