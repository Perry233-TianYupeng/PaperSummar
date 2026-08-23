"""CardStore 单元测试：CRUD、ID 唯一性、原子写、搜索。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.store import CARD_ID_RE, CardStore, generate_card_id  # noqa: E402


@pytest.fixture
def store(tmp_path: Path) -> CardStore:
    return CardStore(tmp_path)


def test_generate_card_id_unique_and_valid() -> None:
    ids = {generate_card_id() for _ in range(50)}
    assert len(ids) == 50  # 唯一
    for cid in ids:
        assert CARD_ID_RE.match(cid) is not None


def test_create_default_title(store: CardStore) -> None:
    card = store.create()
    assert card.title == "新资料卡"
    assert card.id.startswith("card_")
    assert store.get(card.id).id == card.id


def test_create_with_title_and_roundtrip(store: CardStore) -> None:
    card = store.create(title="Attention Is All You Need")
    card.content = "Transformer 架构"
    card.personal_notes = "必读"
    updated = store.update(card)
    assert updated.content == "Transformer 架构"
    reloaded = store.get(card.id)
    assert reloaded.personal_notes == "必读"
    assert reloaded.created_at == updated.created_at  # 保留创建时间


def test_update_keeps_created_at(store: CardStore) -> None:
    card = store.create()
    before = card.created_at
    card.title = "新标题"
    updated = store.update(card)
    assert updated.created_at == before
    assert updated.updated_at >= before


def test_delete(store: CardStore) -> None:
    card = store.create()
    assert store.delete(card.id) is True
    assert store.delete(card.id) is False  # 二次删除返回 False
    with pytest.raises(KeyError):
        store.get(card.id)


def test_invalid_id_rejected(store: CardStore) -> None:
    with pytest.raises(ValueError):
        store._path("../evil")
    with pytest.raises(ValueError):
        store.get("not_a_card_id")


def test_list_sorted_by_creation(store: CardStore) -> None:
    c1 = store.create(title="A")
    c2 = store.create(title="B")
    c3 = store.create(title="C")
    ids = [c.id for c in store.list_cards()]
    assert ids == [c1.id, c2.id, c3.id]


def test_search_title(store: CardStore) -> None:
    store.create(title="Transformer 综述")
    store.create(title="扩散模型")
    hits = store.search("transformer", "title")
    assert len(hits) == 1
    assert hits[0].title == "Transformer 综述"


def test_search_author(store: CardStore) -> None:
    card = store.create(title="X")
    card.authors = "张三, 李四"
    store.update(card)
    hits = store.search("李四", "author")
    assert [c.id for c in hits] == [card.id]


def test_search_content(store: CardStore) -> None:
    card = store.create(title="Y")
    card.content = "提出一种高效的注意力机制"
    store.update(card)
    hits = store.search("注意力机制", "content")
    assert [c.id for c in hits] == [card.id]


def test_blank_search_returns_all(store: CardStore) -> None:
    store.create()
    store.create()
    assert len(store.search("  ", "title")) == 2
