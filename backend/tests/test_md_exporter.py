"""md 导出测试：首行 # card_id、字段齐全、可重复导出。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.models import Card  # noqa: E402
from app.services.md_exporter import export_markdown, render_markdown  # noqa: E402


def make_card(**overrides) -> Card:
    base = {
        "id": "card_20260823_000000_abcd",
        "title": "Attention Is All You Need",
        "arxiv_id": "1706.03762",
        "authors": "Vaswani et al.",
        "content": "提出 Transformer",
        "personal_notes": "值得精读",
    }
    base.update(overrides)
    return Card(**base)


def test_first_line_is_card_id() -> None:
    card = make_card()
    md = render_markdown(card)
    lines = md.splitlines()
    assert lines[0] == "# card_20260823_000000_abcd"


def test_all_fields_present() -> None:
    card = make_card()
    md = render_markdown(card)
    for label in ["论文题目", "Arxiv ID", "作者团队人名", "作者团队信息", "主要作者研究方向",
                  "论文首发时间（Arxiv）", "最终发表期刊/会议", "论文内容", "论文创新点",
                  "代码仓库链接", "个人感想", "AI 总结"]:
        assert f"## {label}" in md
    assert "Attention Is All You Need" in md
    assert "值得精读" in md
    assert "1706.03762" in md


def test_blank_field_marked_unfilled() -> None:
    card = make_card(code_repo="")
    md = render_markdown(card)
    assert "（未填写）" in md


def test_export_writes_file(tmp_path: Path) -> None:
    card = make_card()
    result = export_markdown(card, tmp_path / "exports")
    target = Path(result["path"])
    assert target.exists()
    assert target.read_text(encoding="utf-8").splitlines()[0] == "# card_20260823_000000_abcd"
    assert result["first_line"] == "# card_20260823_000000_abcd"


def test_export_idempotent(tmp_path: Path) -> None:
    card = make_card()
    exports = tmp_path / "exports"
    export_markdown(card, exports)
    export_markdown(card, exports)
    assert len(list(exports.iterdir())) == 1
