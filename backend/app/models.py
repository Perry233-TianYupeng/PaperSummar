"""Pydantic 数据模型：卡片、设置、任务。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# 资料卡中可由 AI 补全填充的字段（个人感想 personal_notes 永不参与）
AI_MERGEABLE_FIELDS: list[str] = [
    "authors",
    "arxiv_first_published",
    "final_venue",
    "content",
    "innovations",
    "code_repo",
]

# 新建卡片时的默认占位标题（不计入"已填写题目"，前后端保持一致）
DEFAULT_TITLE = "新资料卡"

# 卡片全部可编辑字段（展示与编辑顺序）
CARD_FIELDS: list[str] = [
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
    "personal_notes",
    "ai_summary",
]


class Card(BaseModel):
    """一篇论文的资料卡。"""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    arxiv_id: str = ""
    authors: str = ""
    author_team_info: str = ""
    research_directions: str = ""
    arxiv_first_published: str = ""
    final_venue: str = ""
    content: str = ""
    innovations: str = ""
    code_repo: str = ""
    personal_notes: str = ""
    ai_summary: str = ""
    created_at: str = ""
    updated_at: str = ""

    def is_title_filled(self) -> bool:
        """题目是否已填写为真实论文题目（排除默认占位标题）。"""
        title = (self.title or "").strip()
        return bool(title) and title != DEFAULT_TITLE

    def is_blank(self, field: str) -> bool:
        return not (getattr(self, field, None) or "").strip()

    def to_summary(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "updated_at": self.updated_at}


class CardSummary(BaseModel):
    """导航栏列表项（摘要，不携带大文本字段）。"""

    id: str
    title: str
    updated_at: str


class Settings(BaseModel):
    """个人设置（本地 config.json）。api_key 明文仅在本地存储。"""

    model_config = ConfigDict(extra="ignore")

    owner_name: str = ""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    theme: Literal["light", "dark"] = "light"
    data_dir: str = ""

    def has_api_key(self) -> bool:
        return bool(self.api_key and self.api_key.strip())


class SettingsPublic(BaseModel):
    """返回给前端的设置：api_key 做掩码。"""

    owner_name: str
    api_key: str
    base_url: str
    model: str
    theme: str
    data_dir: str


class TaskStatus(str, Enum):
    """任务状态常量。"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Task(BaseModel):
    """一次后台 AI 任务（补全 / 总结 / md 导出）。"""

    model_config = ConfigDict(extra="ignore")

    task_id: str
    kind: str  # ai_completion | ai_summary | md_export
    card_id: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    stage: str = ""
    message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = ""
    finished_at: str = ""

    def update(
        self,
        progress: float | None = None,
        stage: str | None = None,
        message: str | None = None,
    ) -> None:
        if progress is not None:
            self.progress = max(0.0, min(1.0, float(progress)))
        if stage is not None:
            self.stage = stage
        if message is not None:
            self.message = message


def now_iso() -> str:
    """当前时间的本地 ISO 字符串（含时区偏移）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")
