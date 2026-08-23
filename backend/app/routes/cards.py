"""卡片 CRUD 与搜索路由。"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..models import Card
from ..store import CardStore

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _get_store() -> CardStore:
    from ..main import get_store  # 局部导入避免循环

    return get_store()


@router.get("")
def list_cards(
    q: str = Query("", description="搜索关键词，为空返回全部"),
    mode: Literal["title", "author", "content"] = Query("title"),
) -> list[dict[str, str]]:
    """卡片列表摘要；带 q 时按 mode 检索，结果仍返回摘要列表。"""
    store = _get_store()
    cards = store.search(q, mode) if q.strip() else store.list_cards()
    return [c.to_summary() for c in cards]


@router.post("", status_code=201)
def create_card(body: dict | None = None) -> Card:
    """新建卡片。body 可带 title；未填则默认「新资料卡」。"""
    store = _get_store()
    title = (body or {}).get("title", "")
    return store.create(title=title or "")


@router.get("/{card_id}")
def get_card(card_id: str) -> Card:
    store = _get_store()
    try:
        return store.get(card_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"资料卡不存在：{card_id}") from None


@router.put("/{card_id}")
def update_card(card_id: str, card: Card) -> Card:
    """整体保存修改（不关闭卡片）。"""
    store = _get_store()
    if card.id and card.id != card_id:
        raise HTTPException(status_code=400, detail="卡片 ID 与路径不一致")
    card.id = card_id
    try:
        return store.update(card)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"资料卡不存在：{card_id}") from None


@router.delete("/{card_id}")
def delete_card(card_id: str) -> dict[str, bool]:
    store = _get_store()
    if not store.delete(card_id):
        raise HTTPException(status_code=404, detail=f"资料卡不存在：{card_id}")
    return {"ok": True}
