"""卡片 → Markdown 导出。

严格要求：导出文件**首行**为 ``# <card_id>``（无空行、无额外字符），
便于外部工具按 ``# card_`` 切分融合多张卡片的 md 内容。
"""
from __future__ import annotations

from pathlib import Path

from ..models import CARD_FIELDS, Card
from ..utils.logging_setup import get_logger

_logger = get_logger()

_FIELD_LABELS: dict[str, str] = {
    "title": "论文题目",
    "arxiv_id": "Arxiv ID",
    "authors": "作者团队人名",
    "author_team_info": "作者团队信息",
    "research_directions": "主要作者研究方向",
    "arxiv_first_published": "论文首发时间（Arxiv）",
    "final_venue": "最终发表期刊/会议",
    "content": "论文内容",
    "innovations": "论文创新点",
    "code_repo": "代码仓库链接",
    "personal_notes": "个人感想",
    "ai_summary": "AI 总结",
}


def render_markdown(card: Card) -> str:
    """把卡片渲染为 Markdown 文本（首行是 # card_id）。"""
    lines = [f"# {card.id}"]
    for field in CARD_FIELDS:
        value = (getattr(card, field) or "").strip()
        label = _FIELD_LABELS.get(field, field)
        lines.append("")
        lines.append(f"## {label}")
        lines.append(value if value else "（未填写）")
    return "\n".join(lines) + "\n"


def export_markdown(card: Card, exports_dir: Path) -> dict[str, str]:
    """把卡片写入 <exports_dir>/<card_id>.md，返回路径与首行预览。"""
    exports_dir = Path(exports_dir)
    exports_dir.mkdir(parents=True, exist_ok=True)
    target = exports_dir / f"{card.id}.md"
    content = render_markdown(card)
    target.write_text(content, encoding="utf-8")
    _logger.info("已导出 md：%s", target)
    first_line = content.splitlines()[0] if content.splitlines() else ""
    return {"path": str(target), "preview": content[:1000], "first_line": first_line}
