"""AI 补全 / 总结编排：arXiv → DuckDuckGo → LLM → Strict Merge。

核心保证：**已填写的字段绝不会被 AI 删除或修改**。合并逻辑是纯 Python 强制，
只在「卡片字段为空 且 AI 值非空」时才填充；personal_notes 永不参与补全。
"""
from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models import AI_MERGEABLE_FIELDS, Card, Settings, now_iso
from ..utils.logging_setup import get_logger
from .arxiv import ArxivClient, extract_repo_urls
from .llm import LLMClient
from .websearch import (
    DeepSeekWebSearcher,
    TavilySearcher,
    create_searcher,
    snippets_to_text,
)

_logger = get_logger()

Progress = Callable[[float | None, str | None, str | None], None]

COMPLETION_KEYS = ["arxiv_first_published", "final_venue", "content", "innovations"]


def is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def strict_merge(card: Card, ai_values: dict[str, Any]) -> tuple[Card, list[str], list[str]]:
    """把 AI 值严格合并进卡片。

    返回 (合并后的卡片, 被填充的字段列表, 因已填写而被跳过的字段列表)。
    只允许填充 AI_MERGEABLE_FIELDS 中的字段，且必须满足「卡片为空 且 AI 值非空」。
    personal_notes 等其它字段永远不被触碰。
    """
    updated = copy.deepcopy(card)
    filled: list[str] = []
    skipped: list[str] = []

    for field in AI_MERGEABLE_FIELDS:
        raw = ai_values.get(field)
        ai_val = str(raw).strip() if raw is not None else ""
        if updated.is_blank(field):
            if ai_val:
                setattr(updated, field, ai_val)
                filled.append(field)
            else:
                skipped.append(field)
        else:
            skipped.append(field)  # 已填写 → 无论如何跳过

    updated.updated_at = now_iso()
    return updated, filled, skipped


def run_completion(
    card: Card, settings: Settings, data_dir: Path, progress: Progress
) -> dict[str, Any]:
    """执行一次 AI 信息补全（不会触碰 personal_notes 与已填字段）。"""
    # ---- [1] arXiv 查询 ----
    progress(0.1, "arxiv", "正在查询 arXiv ...")
    arxiv = None
    client = ArxivClient()
    try:
        if card.arxiv_id.strip():
            arxiv = client.query_by_id(card.arxiv_id)
        if arxiv is None:
            arxiv = client.query_by_title(card.title)
        if arxiv is None:
            _logger.info("arXiv 未命中，继续走网页搜索与 LLM")
    finally:
        client.close()
    progress(0.35, "arxiv", "arXiv 元数据获取完成")

    # ---- [2] 网页搜索（Tavily 或 DuckDuckGo 兜底） ----
    searcher = create_searcher(settings)
    if isinstance(searcher, TavilySearcher):
        provider = "Tavily"
    elif isinstance(searcher, DeepSeekWebSearcher):
        provider = "DeepSeek"
    else:
        provider = "DuckDuckGo"
    progress(0.4, "web", f"{provider} 网页搜索 ...")
    query_parts = [card.title]
    if card.arxiv_id.strip():
        query_parts.append(card.arxiv_id)
    query_parts.append("paper journal conference published year")
    web_text = snippets_to_text(searcher.search(" ".join(query_parts)))
    progress(0.6, "web", "网页证据收集完成")

    # ---- [3] LLM 结构化输出 ----
    progress(0.65, "llm", "LLM 提取与总结 ...")
    llm = LLMClient(settings.api_key, settings.base_url, settings.model)
    prompt = _build_completion_prompt(card, arxiv, web_text)
    llm_result = llm.chat_json(prompt)
    progress(0.9, "llm", "LLM 结果解析完成")

    # ---- [4] Strict Merge 并写回 ----
    progress(0.92, "merge", "严格合并（绝不覆盖已填内容）...")
    ai_values: dict[str, Any] = {
        "authors": (arxiv.authors if arxiv else ""),
        "arxiv_first_published": llm_result.get("arxiv_first_published")
        or (arxiv.published if arxiv else ""),
        "final_venue": llm_result.get("final_venue") or (arxiv.journal_ref if arxiv else ""),
        "content": llm_result.get("content"),
        "innovations": llm_result.get("innovations"),
        "code_repo": llm_result.get("code_repo")
        or extract_repo_urls((arxiv.summary if arxiv else ""), web_text),
    }
    updated, filled, skipped = strict_merge(card, ai_values)

    from ..store import CardStore  # 局部导入避免循环

    progress(0.97, "merge", "写回磁盘 ...")
    CardStore(data_dir).update(updated)
    progress(1.0, "done", "补全完成")
    return {"filled": filled, "skipped": skipped, "card": updated.model_dump()}


def run_summary(
    card: Card, settings: Settings, data_dir: Path, progress: Progress
) -> dict[str, Any]:
    """生成 AI 总结并写入卡片 ai_summary 字段（随卡片保存/导出）。"""
    progress(0.1, "llm", "正在生成 AI 总结 ...")
    llm = LLMClient(settings.api_key, settings.base_url, settings.model)
    prompt = (
        "请为下面这篇论文写一段 200-300 字的中文总结，覆盖研究问题、核心方法、主要结果与意义。"
        "仅输出 JSON：{\"summary\": \"总结正文\"}。\n\n"
        f"题目：{card.title}\n作者：{card.authors}\n"
        f"论文内容：{card.content or '(未填写)'}\n创新点：{card.innovations or '(未填写)'}\n"
    )
    summary_text = _extract_summary(llm, prompt)
    if not summary_text:
        raise RuntimeError("AI 总结返回为空")

    updated = card.model_copy(update={"ai_summary": summary_text, "updated_at": now_iso()})

    from ..store import CardStore  # 局部导入避免循环

    progress(0.7, "llm", "总结生成完成，写入卡片 ...")
    CardStore(data_dir).update(updated)
    progress(1.0, "done", "AI 总结完成")
    return {"ai_summary": summary_text, "card": updated.model_dump()}


def _extract_summary(llm: LLMClient, prompt: str) -> str:
    """从 LLM 返回中稳健提取总结文本（JSON 优先，失败则取纯文本）。"""
    try:
        result = llm.chat_json(prompt)
        text = str(result.get("summary") or "").strip()
        if text:
            return text
    except Exception as exc:  # noqa: BLE001
        _logger.warning("AI 总结 JSON 提取失败：%s", exc)
    # 纯文本兜底
    try:
        resp = llm._client.chat.completions.create(
            model=llm.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("AI 总结文本兜底失败：%s", exc)
        return ""


def _build_completion_prompt(card: Card, arxiv, web_text: str) -> str:
    """构造补全 prompt：要求仅输出 4 个键的 JSON。"""
    known_fields = [
        "title",
        "arxiv_id",
        "authors",
        "author_team_info",
        "research_directions",
        "arxiv_first_published",
        "final_venue",
        "content",
        "innovations",
        "code_repo",
    ]
    fields_section = "已知（已填写）字段：\n" + "\n".join(
        f"- {k}：{(getattr(card, k) or '')[:500]}" for k in known_fields
    )
    arxiv_section = (
        "\narXiv 元数据：\n" + "\n".join(f"- {k}：{v}" for k, v in arxiv.to_llm_context().items())
        if arxiv
        else "\narXiv 无结果。"
    )

    return f"""请根据以下资料，补全这篇论文的信息，仅输出 JSON，含且仅含以下 4 个键：
- arxiv_first_published：论文在 arXiv 的首发时间（年月日，未查到可留空）
- final_venue：最终发表的期刊或会议名称（不确定时注明"推测"；查不到可留空）
- content：论文内容摘要（200-300 字，介绍问题、方法、结果）
- innovations：论文创新点（分点，每点一句话，共 2-4 点）

论文题目：{card.title}
arXiv ID：{card.arxiv_id or '(未填写)'}
{fields_section}
{arxiv_section}
网页检索证据：
{web_text[:3000] if web_text else '(无)'}

请以 JSON 输出，不要输出其它内容。"""
