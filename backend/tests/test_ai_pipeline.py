"""AI 补全核心保证测试：已填字段绝不被覆盖、personal_notes 永不参与。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.models import Card  # noqa: E402
from app.services.ai_pipeline import is_blank, strict_merge  # noqa: E402


def make_card(**overrides) -> Card:
    base = {
        "id": "card_20260823_000000_abcd",
        "title": "Attention Is All You Need",
    }
    base.update(overrides)
    return Card(**base)


class TestStrictMerge:
    def test_fills_only_blank_fields(self) -> None:
        card = make_card(content="", innovations="", authors="")
        ai = {
            "content": "AI 生成的内容",
            "innovations": "AI 生成的创新点",
            "authors": "AI 生成的作者（authors 在可合并字段中，空时应填充）",
            "final_venue": "",  # 空值不填充
        }
        updated, filled, skipped = strict_merge(card, ai)
        assert updated.content == "AI 生成的内容"
        assert updated.innovations == "AI 生成的创新点"
        assert updated.authors == "AI 生成的作者（authors 在可合并字段中，空时应填充）"
        assert "content" in filled and "innovations" in filled and "authors" in filled
        assert "final_venue" in skipped

    def test_existing_field_never_overwritten(self) -> None:
        card = make_card(content="用户手写的内容，很重要", innovations="")
        ai = {"content": "AI 想覆盖的内容", "innovations": "AI 创新点"}
        updated, filled, skipped = strict_merge(card, ai)
        assert updated.content == "用户手写的内容，很重要"  # 未被覆盖
        assert updated.innovations == "AI 创新点"
        assert "content" in skipped
        assert "content" not in filled

    def test_personal_notes_never_touched(self) -> None:
        card = make_card(personal_notes="我的感想：强烈推荐")
        ai = {"personal_notes": "AI 想篡改的感想"}
        updated, _, _ = strict_merge(card, ai)
        assert updated.personal_notes == "我的感想：强烈推荐"  # 原样保留

    def test_ai_blank_values_do_not_fill(self) -> None:
        card = make_card(content="", final_venue="")
        ai = {"content": "", "final_venue": "   "}
        updated, filled, skipped = strict_merge(card, ai)
        assert updated.content == ""
        assert updated.final_venue == ""
        assert filled == []

    def test_code_repo_only_filled_when_blank(self) -> None:
        card = make_card(code_repo="https://github.com/user/repo")
        ai = {"code_repo": "https://github.com/other/repo"}
        updated, _, _ = strict_merge(card, ai)
        assert updated.code_repo == "https://github.com/user/repo"  # 已填则保留

    def test_filled_tracking_accurate(self) -> None:
        card = make_card(
            authors="已有作者", content="", innovations="", arxiv_first_published=""
        )
        ai = {
            "authors": "A",
            "content": "C",
            "innovations": "I",
            "arxiv_first_published": "2023-01-01",
        }
        updated, filled, skipped = strict_merge(card, ai)
        # filled/skipped 顺序遵循 AI_MERGEABLE_FIELDS 定义顺序
        assert filled == ["arxiv_first_published", "content", "innovations"]
        assert skipped == ["authors", "final_venue", "code_repo"]
        assert updated.authors == "已有作者"  # 已填不被覆盖


class TestIsBlank:
    def test_values(self) -> None:
        assert is_blank(None)
        assert is_blank("")
        assert is_blank("   ")
        assert not is_blank("文本")
        assert not is_blank(0)
        assert not is_blank(False)
