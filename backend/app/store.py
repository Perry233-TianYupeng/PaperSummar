"""卡片存储：CRUD、ID 生成、原子写入、线程锁。

存储布局：``<data_dir>/cards/card_<timestamp>_<rand>.json``，每卡一个文件。
CardStore 持一把全局锁串行化所有写操作，避免 AI 后台线程与用户手动保存并发覆盖。
"""
from __future__ import annotations

import re
import secrets
import threading
from datetime import datetime, timedelta
from pathlib import Path

from .models import DEFAULT_TITLE, Card
from .utils.atomic_io import atomic_write_json, read_json

CARD_ID_RE = re.compile(r"^card_[0-9]{8}_[0-9]{6}_[0-9a-f]{4}$")
_CARD_PREFIX = "card_"


def generate_card_id(now: datetime | None = None) -> str:
    """生成卡片 ID：card_YYYYMMDD_HHMMSS_<4位hex>。时间戳前缀天然排序。"""
    now = now or datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(2)  # 4 位十六进制
    return f"{_CARD_PREFIX}{stamp}_{rand}"


class CardStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.cards_dir = self.data_dir / "cards"
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._last_stamp = ""  # 保证同进程内时间戳严格递增，列表排序稳定

    # ---------- 内部 ----------

    def _path(self, card_id: str) -> Path:
        if not CARD_ID_RE.match(card_id):
            raise ValueError(f"非法卡片 ID：{card_id}")
        return self.cards_dir / f"{card_id}.json"

    def _read(self, card_id: str) -> Card:
        raw = read_json(self._path(card_id), default=None)
        if raw is None:
            raise KeyError(card_id)
        return Card(**raw)

    # ---------- 查询 ----------

    def list_cards(self) -> list[Card]:
        """按创建时间（文件名时间戳前缀）升序返回全部卡片。"""
        result: list[Card] = []
        for f in sorted(self.cards_dir.glob("card_*.json")):
            try:
                result.append(Card(**read_json(f, default={})))
            except Exception:
                continue  # 单个损坏文件不阻塞列表
        return result

    def list_summaries(self) -> list[dict[str, str]]:
        return [c.to_summary() for c in self.list_cards()]

    def get(self, card_id: str) -> Card:
        with self._lock:
            return self._read(card_id)

    # ---------- 写操作（全部持锁） ----------

    def create(self, title: str = "") -> Card:
        """新建卡片，默认标题“新资料卡”。

        时间戳保证严格递增（同秒内连续创建自动 +1 秒），ID 唯一且列表排序稳定；
        若与磁盘已有文件冲突则继续后移，覆盖重启后的极端情况。
        """
        with self._lock:
            now = datetime.now().astimezone()
            stamp = now.strftime("%Y%m%d_%H%M%S")
            while stamp <= self._last_stamp:
                now = now + timedelta(seconds=1)
                stamp = now.strftime("%Y%m%d_%H%M%S")
            self._last_stamp = stamp

            card_id = generate_card_id(now)
            while self._path(card_id).exists():  # 与已有文件冲突 → 时间戳后移
                now = now + timedelta(seconds=1)
                card_id = generate_card_id(now)
            card = Card(
                id=card_id,
                title=title or DEFAULT_TITLE,
                created_at=now.isoformat(timespec="seconds"),
                updated_at=now.isoformat(timespec="seconds"),
            )
            self._write(card)
            return card

    def update(self, card: Card) -> Card:
        """整体保存修改（不关闭卡片）。以请求体为准，更新时间戳。"""
        with self._lock:
            existing = self._read(card.id)
            payload = card.model_dump()
            payload["created_at"] = existing.created_at
            payload["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            updated = Card(**payload)
            self._write(updated)
            return updated

    def delete(self, card_id: str) -> bool:
        with self._lock:
            path = self._path(card_id)
            if path.exists():
                path.unlink()
                return True
            return False

    def _write(self, card: Card) -> None:
        atomic_write_json(self._path(card.id), card.model_dump())

    # ---------- 搜索 ----------

    def search(self, q: str, mode: str) -> list[Card]:
        """按 题目(title) / 作者(author) / 内容(content) 检索。

        内容模式匹配 content + innovations（论文内容与创新点）。
        """
        q = (q or "").strip().lower()
        if not q:
            return self.list_cards()
        cards = self.list_cards()
        mode = mode or "title"

        def hit(card: Card) -> bool:
            if mode == "author":
                haystack = f"{card.authors} {card.author_team_info}"
            elif mode == "content":
                haystack = f"{card.content} {card.innovations}"
            else:  # title
                haystack = f"{card.title} {card.arxiv_id}"
            return q in haystack.lower()

        return [c for c in cards if hit(c)]
