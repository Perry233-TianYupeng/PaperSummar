"""AI 补全核心保证测试：已填字段绝不被覆盖、personal_notes 永不参与。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.models import Card, Settings  # noqa: E402
from app.services.ai_pipeline import (  # noqa: E402
    _first_authors,
    _format_numbered_list,
    is_blank,
    strict_merge,
)


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
            "author_team_info": "团队信息",
            "research_directions": "研究方向",
        }
        updated, filled, skipped = strict_merge(card, ai)
        # filled/skipped 顺序遵循 AI_MERGEABLE_FIELDS 定义顺序
        assert filled == [
            "author_team_info",
            "research_directions",
            "arxiv_first_published",
            "content",
            "innovations",
        ]
        assert skipped == ["authors", "final_venue", "code_repo"]
        assert updated.authors == "已有作者"  # 已填不被覆盖
        assert updated.author_team_info == "团队信息"
        assert updated.research_directions == "研究方向"


class TestFirstAuthors:
    def test_comma_separated(self) -> None:
        assert _first_authors("Alice, Bob, Carol, Dave", n=3) == ["Alice", "Bob", "Carol"]

    def test_chinese_separators(self) -> None:
        assert _first_authors("张三、李四、王五", n=3) == ["张三", "李四", "王五"]

    def test_empty(self) -> None:
        assert _first_authors("") == []
        assert _first_authors("   ") == []

    def test_limit(self) -> None:
        assert _first_authors("A and B and C and D", n=2) == ["A", "B"]


class TestFormatNumberedList:
    def test_adds_numbers_to_plain_lines(self) -> None:
        out = _format_numbered_list("创新点一\n创新点二")
        assert out == "1. 创新点一\n2. 创新点二"

    def test_keeps_existing_numbers(self) -> None:
        out = _format_numbered_list("1. 已有\n3. 保持")
        assert out == "1. 已有\n3. 保持"

    def test_strips_bullets(self) -> None:
        out = _format_numbered_list("- 一\n• 二")
        assert out == "1. 一\n2. 二"

    def test_empty(self) -> None:
        assert _format_numbered_list("") == ""
        assert _format_numbered_list("   ") == ""


class TestIsBlank:
    def test_values(self) -> None:
        assert is_blank(None)
        assert is_blank("")
        assert is_blank("   ")
        assert not is_blank("文本")
        assert not is_blank(0)
        assert not is_blank(False)


class TestRunCompletionIntegration:
    """端到端验证 run_completion：作者信息填充 + 创新点编号格式 + 已填字段保护。"""

    def test_fills_author_info_and_formats_innovations(self, tmp_path, monkeypatch) -> None:
        import app.store as store_mod
        from app.services import ai_pipeline
        from app.services.websearch import SearchResult

        # --- 假 arXiv：提供三位作者 ---
        class FakeArxiv:
            authors = "张三, 李四, 王五"
            published = "2017-06-12"
            journal_ref = "NeurIPS 2017"
            summary = "摘要内容"
            title = "Attention Is All You Need"
            arxiv_id = "1706.03762"

            def to_llm_context(self):
                return {
                    "title": self.title, "authors": self.authors,
                    "published": self.published, "journal_ref": self.journal_ref,
                    "abstract": self.summary,
                }

        class FakeArxivClient:
            def __init__(self, *a, **kw):
                pass

            def query_by_id(self, _id):
                return FakeArxiv()

            def query_by_title(self, _t):
                return None

            def close(self):
                pass

        # --- 假搜索：记录被搜索的作者名，并返回该作者的学术信息片段 ---
        searched_queries: list[str] = []

        class FakeSearcher:
            def search(self, query: str):
                searched_queries.append(query)
                return [
                    SearchResult(
                        title="Google Scholar",
                        url="http://x",
                        snippet="张三：引用量 50000，主攻自然语言处理，单位某大学",
                    )
                ]

        # --- 假 LLM：校验 prompt 含作者信息，返回 6 键 ---
        class FakeLLM:
            def __init__(self, *a, **kw):
                pass

            def chat_json(self, prompt):
                assert "张三" in prompt  # 作者学术信息已传入 prompt
                assert "author_team_info" in prompt
                assert "research_directions" in prompt
                assert "innovations" in prompt
                return {
                    "arxiv_first_published": "2017-06-12",
                    "final_venue": "NeurIPS 2017",
                    "content": "提出 Transformer 架构",
                    "innovations": "创新一\n创新二",  # 无编号，应被格式化
                    "author_team_info": "张三：引用量高，单位某大学\n李四：主攻机器学习",
                    "research_directions": "张三：自然语言处理\n李四：机器学习",
                }

        # --- 假存储：捕获写入的卡片 ---
        class FakeStore:
            def __init__(self, *a, **kw):
                self.saved = None

            def update(self, card):
                self.saved = card
                return card

        monkeypatch.setattr(ai_pipeline, "ArxivClient", FakeArxivClient)
        monkeypatch.setattr(ai_pipeline, "create_searcher", lambda settings: FakeSearcher())
        monkeypatch.setattr(ai_pipeline, "LLMClient", FakeLLM)
        monkeypatch.setattr(store_mod, "CardStore", FakeStore)

        card = Card(
            id="card_20260824_000000_abcd",
            title="Attention Is All You Need",
            arxiv_id="1706.03762",  # 命中 arXiv，提供三位作者
        )
        settings = Settings()
        result = ai_pipeline.run_completion(card, settings, tmp_path, lambda *a, **kw: None)

        # 前三位作者都被搜索了
        assert any("张三" in q for q in searched_queries)
        assert any("李四" in q for q in searched_queries)
        assert any("王五" in q for q in searched_queries)

        saved = result["card"]
        assert saved["author_team_info"].startswith("张三：")
        assert saved["research_directions"].startswith("张三：")
        assert saved["innovations"] == "1. 创新一\n2. 创新二"  # 编号格式
        # filled 记录
        assert "author_team_info" in result["filled"]
        assert "research_directions" in result["filled"]
        assert "innovations" in result["filled"]
